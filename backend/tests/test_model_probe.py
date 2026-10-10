"""真实 SDK 检测两种协议，HTTP 层替身保证验收不调用外部供应商。"""

import json

import httpx
import httpx2
import pytest
from langchain_core.messages import AIMessage, AIMessageChunk

from app.config import ModelSettings
from app.model_probe import probe_capabilities


def completion(protocol, *, tool=False):
    if protocol == "anthropic":
        content = (
            [
                {
                    "type": "tool_use",
                    "id": "check-1",
                    "name": "connection_check",
                    "input": {"value": "ok"},
                }
            ]
            if tool
            else [{"type": "text", "text": "检测成功"}]
        )
        return {
            "id": "probe",
            "type": "message",
            "role": "assistant",
            "model": "main",
            "content": content,
            "stop_reason": "tool_use" if tool else "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }
    message = {"role": "assistant", "content": None if tool else "检测成功"}
    if tool:
        message["tool_calls"] = [
            {
                "id": "check-1",
                "type": "function",
                "function": {"name": "connection_check", "arguments": '{"value":"ok"}'},
            }
        ]
    return {
        "id": "probe",
        "object": "chat.completion",
        "created": 0,
        "model": "main",
        "choices": [
            {"index": 0, "message": message, "finish_reason": "tool_calls" if tool else "stop"}
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    }


def streaming(protocol):
    if protocol == "openai":
        chunks = [
            {
                "id": "probe",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": "main",
                "choices": [{"index": 0, "delta": {"content": part}, "finish_reason": None}],
            }
            for part in ("流式", "成功")
        ]
        chunks.append(
            {
                "id": "probe",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": "main",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
        )
        return "".join(f"data: {json.dumps(row)}\n\n" for row in chunks) + "data: [DONE]\n\n"
    start = completion(protocol)
    start.update(content=[], stop_reason=None, usage={"input_tokens": 5, "output_tokens": 0})
    events = [
        ("message_start", {"type": "message_start", "message": start}),
        (
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        ),
    ]
    events.extend(
        (
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": part},
            },
        )
        for part in ("流式", "成功")
    )
    events.extend(
        [
            ("content_block_stop", {"type": "content_block_stop", "index": 0}),
            (
                "message_delta",
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                    "usage": {"output_tokens": 5},
                },
            ),
            ("message_stop", {"type": "message_stop"}),
        ]
    )
    return "".join(f"event: {event}\ndata: {json.dumps(row)}\n\n" for event, row in events)


@pytest.mark.parametrize("protocol", ["openai", "anthropic"])
async def test_sdk_probe_streaming_tool_roundtrip_and_separate_summary(monkeypatch, protocol):
    transport_api = httpx2 if protocol == "anthropic" else httpx
    requests = []

    def response(request):
        body = json.loads(request.content)
        requests.append(body)
        if body.get("stream"):
            return transport_api.Response(
                200, text=streaming(protocol), headers={"content-type": "text/event-stream"}
            )
        has_result = any(
            row.get("role") == "tool"
            or any(
                part.get("type") == "tool_result"
                for part in (row.get("content") or [])
                if isinstance(part, dict)
            )
            for row in body["messages"]
        )
        return transport_api.Response(
            200, json=completion(protocol, tool=bool(body.get("tools")) and not has_result)
        )

    transport = transport_api.MockTransport(response)

    async def send(_self, request):
        return await transport.handle_async_request(request)

    monkeypatch.setattr(transport_api.AsyncHTTPTransport, "handle_async_request", send)
    settings = ModelSettings(
        protocol=protocol,
        base_url="https://test.invalid/v1",
        model="main",
        summary_model="compress",
        api_key="test-only-key",
    )
    result = await probe_capabilities(settings)
    assert result["ok"] and result["connection_ok"], result["checks"]
    assert [row["status"] for row in result["checks"]] == ["passed"] * 4
    assert result["checks"][1]["detail"] == "收到 2 个文本片段"
    assert len(requests) == 5
    assert [row["model"] for row in requests] == ["main"] * 4 + ["compress"]
    budget_field = "max_tokens" if protocol == "anthropic" else "max_completion_tokens"
    assert all(row[budget_field] == 256 for row in requests)
    assert "test-only-key" not in json.dumps(result)


class FakeModel:
    def __init__(self, failure, summary=False):
        self.failure, self.summary, self.choice = failure, summary, None

    def bind_tools(self, _tools, tool_choice=None):
        self.choice = tool_choice
        return self

    async def ainvoke(self, _question):
        if self.failure == "reply" and not self.summary:
            raise RuntimeError("凭据 test-only-key 失效")
        if self.summary and self.failure == "summary":
            raise RuntimeError("压缩模型不存在 test-only-key")
        if self.choice:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "connection_check",
                        "id": "test",
                        "args": {"value": "bad" if self.failure == "tools" else "ok"},
                    }
                ],
            )
        if self.failure == "truncation":
            return AIMessage(content="a" * 198 + "test-only-key" + "结束")
        return AIMessage(content="成功")

    async def astream(self, _question):
        if self.failure == "streaming":
            raise RuntimeError("不支持流式 test-only-key")
        yield AIMessageChunk(content="成功")


@pytest.mark.parametrize("failure", ["reply", "streaming", "tools", "summary", "truncation"])
async def test_partial_capabilities_redact_credentials_and_close_owned_models(monkeypatch, failure):
    owned, closed = [], []

    def create(_settings, *, summary=False):
        model = FakeModel(failure, summary)
        owned.append(model)
        return model

    async def close(models):
        closed.extend(models)

    monkeypatch.setattr("app.provider.create_model", create)
    monkeypatch.setattr("app.provider.close_models", close)
    result = await probe_capabilities(ModelSettings(api_key="test-only-key"))
    assert closed == owned
    assert "test-only-key" not in json.dumps(result)
    checks = {row["id"]: row["status"] for row in result["checks"]}
    if failure == "reply":
        assert not result["connection_ok"]
        assert list(checks.values()) == ["failed", "not_run", "not_run", "not_run"]
        assert len(owned) == 1
    elif failure != "truncation":
        assert result["connection_ok"] and not result["ok"]
        assert checks[failure] == "failed"
        assert list(checks.values()).count("passed") == 3
    else:
        assert result["ok"]
        assert "test-on" not in result["reply"]
