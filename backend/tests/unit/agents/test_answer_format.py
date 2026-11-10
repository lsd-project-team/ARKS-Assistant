from types import SimpleNamespace

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.runtime.answer_format import AnswerFormatValidation
from tests.helpers.models import DeterministicModel


@pytest.mark.parametrize(
    "content,blocks,passed,call_count",
    [
        ("**" + "完整保留模型选择的长段落。" * 30 + "**", 0, True, 1),
        ("| 参数 | 数值 |\n| --- | --- |\n| 等待 | 0 |", 0, True, 1),
        (
            '```rich-content\n{"version":1,"blocks":[{"id":"a","type":"text",'
            '"content":"正文"}]}\n```',
            1,
            True,
            1,
        ),
        ('```rich-content\n{"version":9,"blocks":[]}\n```', 1, False, 1),
        ("```rich-content\n{坏JSON}\n```", 1, False, 2),
        ('```rich-content\n{"version":1,"blocks":[]}', 1, False, 2),
        ('```rich-content\n{"version":1,"blocks":[{"id":"a","type":"iframe"}]}\n```', 1, False, 1),
        ("````markdown\n```rich-content\n{只是示例}\n```\n````", 0, True, 1),
        ('```json\n{"version":9,"blocks":[]}\n```', 0, True, 1),
    ],
)
async def test_valid_content_avoids_retries_and_broken_syntax_has_only_one_attempt(
    content, blocks, passed, call_count
):
    events, calls = [], []
    answer = AIMessage(content=content)
    response = SimpleNamespace(result=[answer])

    async def handler(request):
        calls.append(request)
        return response

    request = ModelRequest(model=DeterministicModel(), messages=[HumanMessage(content="原问题")])
    result = await AnswerFormatValidation(lambda *event: events.append(event)).awrap_model_call(
        request, handler
    )
    assert len(calls) == call_count and calls[0] is request
    assert len(request.messages) == 1
    assert result is response and answer.text == content
    kind, report = events[0]
    assert kind == "answer_format_validation"
    assert report["blocks"] == blocks and report["passed"] is passed
    assert bool(report["errors"]) is not passed


async def test_missing_json_closer_is_repaired_with_same_ids_and_values_without_fact_review():
    good = (
        '```rich-content\n{"version":1,"blocks":[{"id":"steps","type":"text",'
        '"content":"原始高度280～300，单位未知"}]}\n```'
    )
    broken = good.replace("}]}\n```", "}]\n```")
    events, calls = [], []
    request = ModelRequest(model=DeterministicModel(), messages=[HumanMessage(content="给出步骤")])

    async def handler(current):
        calls.append(current)
        if len(calls) == 2:
            assert current.messages[-2].text == broken
            assert "只修复JSON" in current.messages[-1].text
            assert "不进行结论复核" in current.messages[-1].text
        return SimpleNamespace(result=[AIMessage(content=broken if len(calls) == 1 else good)])

    result = await AnswerFormatValidation(lambda *event: events.append(event)).awrap_model_call(
        request, handler
    )
    assert result.result[0].text == good and len(calls) == 2
    assert [row["passed"] for _, row in events] == [False, True]
    assert request.messages[0].text == "给出步骤" and len(request.messages) == 1


async def test_incomplete_stream_is_not_sent_to_format_repair():
    calls = []
    message = AIMessage(
        content='```rich-content\n{"version":1',
        additional_kwargs={"answer_completion": {"output": "incomplete"}},
    )

    async def handler(request):
        calls.append(request)
        return SimpleNamespace(result=[message])

    await AnswerFormatValidation(lambda *_: None).awrap_model_call(None, handler)
    assert calls == [None]


async def test_intermediate_tool_request_is_not_reported_as_a_final_answer():
    events = []
    answer = AIMessage(
        content="",
        tool_calls=[{"id": "read", "name": "read_source", "args": {"path": "Program.cs"}}],
    )
    response = SimpleNamespace(result=[answer])

    async def handler(_request):
        return response

    result = await AnswerFormatValidation(lambda *event: events.append(event)).awrap_model_call(
        None, handler
    )
    assert result is response and not events
