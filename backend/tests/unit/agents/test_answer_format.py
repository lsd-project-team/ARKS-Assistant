from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.agents.runtime.answer_format import AnswerFormatValidation


@pytest.mark.parametrize(
    "content,blocks,passed",
    [
        ("**" + "完整保留模型选择的长段落。" * 30 + "**", 0, True),
        ("| 参数 | 数值 |\n| --- | --- |\n| 等待 | 0 |", 0, True),
        (
            '```rich-content\n{"version":1,"blocks":[{"id":"a","type":"text",'
            '"content":"正文"}]}\n```',
            1,
            True,
        ),
        ('```rich-content\n{"version":9,"blocks":[]}\n```', 1, False),
        ("```rich-content\n{坏JSON}\n```", 1, False),
        ('```rich-content\n{"version":1,"blocks":[]}', 1, False),
        ('```rich-content\n{"version":1,"blocks":[{"id":"a","type":"iframe"}]}\n```', 1, False),
        ("````markdown\n```rich-content\n{只是示例}\n```\n````", 0, True),
        ('```json\n{"version":9,"blocks":[]}\n```', 0, True),
    ],
)
async def test_format_validation_preserves_content_without_another_model_call(
    content, blocks, passed
):
    events, calls = [], []
    answer = AIMessage(content=content)
    response = SimpleNamespace(result=[answer])

    async def handler(request):
        calls.append(request)
        return response

    result = await AnswerFormatValidation(lambda *event: events.append(event)).awrap_model_call(
        "original-request", handler
    )
    assert calls == ["original-request"]
    assert result is response and answer.text == content
    kind, report = events[0]
    assert kind == "answer_format_validation"
    assert report["blocks"] == blocks and report["passed"] is passed
    assert bool(report["errors"]) is not passed


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
