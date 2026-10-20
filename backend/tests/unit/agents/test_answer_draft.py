from types import SimpleNamespace

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage

from app.agents.runtime.answer_draft import FlowAnswerDraft
from tests.helpers.models import DeterministicModel

REF = "[依据](source:Program.cs#L1-L3)"
LONG = "流程背景。" * 350 + REF
SHORT = "先准备，失败则返回；准备通过后发起Start调用。" + REF


async def compose(reply=SHORT, text=LONG, question="给设备启动流程", limit=10000):
    events, sent = [], []

    class Model:
        async def ainvoke(self, messages, **kwargs):
            sent.append((messages, kwargs))
            if isinstance(reply, BaseException):
                raise reply
            return AIMessage(content=reply)

    async def handler(_):
        return ModelResponse(result=[AIMessage(content=text)])

    draft = FlowAnswerDraft(
        Model(),
        question,
        SimpleNamespace(code_change_ids=[], required=True),
        lambda *e: events.append(e),
        limit,
    )
    result = await draft.awrap_model_call(
        ModelRequest(model=DeterministicModel(), messages=[]), handler
    )
    return result.result[0].text, events, sent


async def test_short_draft_is_not_published_as_fact_checked_answer():
    text, events, sent = await compose()
    assert text == SHORT
    assert len(sent) == 1 and sent[0][1]["config"]["metadata"]["lc_source"] == "answer_draft"
    assert all(kind != "answer_replace" for kind, _ in events)
    assert events[-1][1]["scope"] == "待事实核查的流程短稿"


@pytest.mark.parametrize(
    "reply",
    ["", LONG, "擅自引用其他路径的新结论。[依据](source:Other.cs#L1)", RuntimeError("do-not-echo")],
)
async def test_invalid_or_failed_composition_keeps_original_for_fact_check(reply):
    text, events, _ = await compose(reply)
    assert text == LONG and "do-not-echo" not in str(events)
    assert events[-1][1]["changed"] is False


@pytest.mark.parametrize(
    "question,text,limit",
    [
        ("逐字提取流程原文", LONG, 10000),
        ("设备启动流程", SHORT, 10000),
        ("解释变量", LONG, 10000),
        ("设备启动流程", LONG, 1),
    ],
)
async def test_short_verbatim_nonflow_or_budget_does_not_call_composer(question, text, limit):
    result, _, sent = await compose(question=question, text=text, limit=limit)
    assert result == text and sent == []
