"""验证连续及重叠运行的连接生命周期；请求走真实 SDK，网络传输使用确定性响应。"""

import httpx
import httpx2
import pytest

from app.config import ModelSettings
from app.provider import close_models, create_model


@pytest.mark.parametrize("protocol", ["anthropic", "openai"])
@pytest.mark.parametrize("overlap", [False, True])
async def test_closing_one_model_does_not_break_next_or_overlapping_call(
    monkeypatch, protocol, overlap
):
    calls = []
    transport_api = httpx2 if protocol == "anthropic" else httpx

    def response(request):
        calls.append(request.url.path)
        if protocol == "anthropic":
            payload = {
                "id": "test-message",
                "type": "message",
                "role": "assistant",
                "model": "test-model",
                "content": [{"type": "text", "text": "连接可继续使用"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 3, "output_tokens": 3},
            }
        else:
            payload = {
                "id": "test-message",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "连接可继续使用"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 3, "total_tokens": 6},
            }
        return transport_api.Response(200, json=payload)

    transport = transport_api.MockTransport(response)

    async def send(_self, request):
        return await transport.handle_async_request(request)

    monkeypatch.setattr(transport_api.AsyncHTTPTransport, "handle_async_request", send)
    settings = ModelSettings(
        protocol=protocol,
        base_url="https://test.invalid/v1",
        model="test-model",
        api_key="test-only-key",
    )
    first = create_model(settings)
    second = create_model(settings) if overlap else None
    try:
        assert (await first.ainvoke("第一次请求")).text == "连接可继续使用"
        await close_models([first])
        second = second or create_model(settings)
        assert (await second.ainvoke("第二次请求")).text == "连接可继续使用"
        assert len(calls) == 2
    finally:
        await close_models([first, second] if second else [first])
