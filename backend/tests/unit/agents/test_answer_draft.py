import json
from types import SimpleNamespace

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage

from app.agents.runtime.answer_draft import FlowAnswerDraft
from app.agents.runtime.flow_layout import layout_problem, main_text, source_targets
from app.modules.chat.rich_presentation import project_rich_content, rich_documents
from tests.helpers.models import DeterministicModel

REF = "[依据](source:Program.cs#L1-L3)"
LONG = "流程背景。" * 350 + REF
SHORT = "先准备，失败则返回；准备通过后发起Start调用。" + REF


async def compose(reply=SHORT, text=LONG, question="给设备启动流程", limit=10000):
    events, sent = [], []

    class Model:
        async def ainvoke(self, messages, **kwargs):
            sent.append((messages, kwargs))
            selected = reply.pop(0) if isinstance(reply, list) else reply
            if isinstance(selected, BaseException):
                raise selected
            return AIMessage(content=selected)

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
async def test_failed_composition_keeps_complete_original_and_reports_failure(reply):
    text, events, _ = await compose(reply)
    assert LONG in project_rich_content(text)
    assert "未完成流程整理" in text and "do-not-echo" not in str(events)
    assert events[-1][1]["status"] == "failed"
    document = next(doc for _, _, doc in rich_documents(text))
    assert document.blocks[0].type == "collapsible" and not document.blocks[0].default_open


@pytest.mark.parametrize(
    "question,text,limit",
    [
        ("逐字提取流程原文", LONG, 10000),
        ("设备启动流程", SHORT, 10000),
        ("解释变量", LONG, 10000),
        ("详细解释设备启动流程", LONG, 10000),
    ],
)
async def test_short_verbatim_nonflow_or_budget_does_not_call_composer(question, text, limit):
    result, _, sent = await compose(question=question, text=text, limit=limit)
    assert result == text and sent == []


async def test_budget_failure_is_explicit_and_does_not_drop_original():
    result, events, sent = await compose(limit=1)
    assert not sent and events[-1][1]["code"] == "input_budget"
    assert "未完成流程整理" in result and LONG in project_rich_content(result)


def flow(description="先保存参数，条件通过才启动；取消直接返回。", details=None):
    step = {
        "id": "one",
        "title": "开始",
        "description": description,
        "sources": [{"path": "Program.cs", "start_line": 1, "end_line": 3}],
    }
    if details:
        step["details"] = details
    return (
        "```rich-content\n"
        + json.dumps(
            {"version": 1, "blocks": [{"id": "flow", "type": "step_flow", "steps": [step]}]},
            ensure_ascii=False,
        )
        + "\n```"
    )


async def test_compact_flow_with_long_closed_details_is_kept_without_another_model_call():
    original = flow(details="补充实现，仅供深入核对。" * 300)
    result, _, sent = await compose(text=original)
    assert result == original and not sent
    assert len(original) > 1500 and len(main_text(original)) < 200


async def test_short_flow_with_invalid_extra_block_is_repaired_using_copied_source_objects():
    broken = (
        '```rich-content\n{"version":1,"blocks":[{"id":"bad","type":"overview_grid",'
        '"items":[{"id":"x","title":"入口","description":"查看",'
        '"source":"Program.cs:1-3"}]}]}\n```'
    )
    revised = flow()
    original = revised + "\n" + broken
    result, _, sent = await compose(text=original, reply=revised)
    assert result == revised and len(sent) == 1
    payload = json.loads(sent[0][0][-1].text)
    assert payload["allowed_sources"] == [{"path": "Program.cs", "start_line": 1, "end_line": 3}]
    hint = layout_problem(broken, original, "给流程")
    assert "source" in hint and "Program.cs:1-3" not in hint


async def test_plain_flow_gets_rich_structure_and_invalid_first_revision_can_retry():
    original = "先准备，检查条件；取消直接返回；开始后按所选类型执行，最后停止与保存。" * 9 + REF
    revised = flow()
    result, events, sent = await compose(text=original, reply=["", revised])
    assert result == revised and len(sent) == 2
    assert "结构" in sent[1][0][-1].text or "主阅读区" in sent[1][0][-1].text
    assert events[-1][1]["changed"] is True


async def test_explicit_plain_markdown_uses_no_cards_even_when_composition_fails():
    original = flow()
    result, _, sent = await compose(text=original, question="用纯Markdown说明流程")
    assert not sent and result == project_rich_content(original)
    result, _, _ = await compose(reply=RuntimeError(), question="用纯Markdown说明流程")
    assert "未完成流程整理" in result and LONG in result and not list(rich_documents(result))
    assert "纯Markdown" in layout_problem(original, original, "用纯Markdown说明流程")


async def test_rewriter_cannot_hide_the_entire_flow_or_forge_source_locations():
    original = flow()
    hidden = {
        "version": 1,
        "blocks": [
            {
                "id": "hidden",
                "type": "collapsible",
                "title": "详情",
                "blocks": [{"id": "text", "type": "text", "content": "补充说明。" * 60 + REF}],
            }
        ],
    }
    content = "\n```rich-content\n" + json.dumps(hidden) + "\n```"
    assert "step_flow" in layout_problem(content, original, "给设备流程")
    result, _, sent = await compose(text=content, reply=original)
    assert result == original and len(sent) == 1
    assert "引用" in layout_problem(
        original.replace('"start_line": 1', '"start_line": 2'), original, "给流程"
    )
    assert source_targets(flow()) == source_targets(REF)


async def test_long_structured_flow_is_reorganized_without_losing_rich_content():
    document = {
        "version": 1,
        "blocks": [
            {
                "id": "stop",
                "type": "step_flow",
                "steps": [
                    {
                        "id": "stop-flag",
                        "title": "停止",
                        "description": "保留前置条件与停止分支。" * 140,
                        "sources": [{"path": "Program.cs", "start_line": 1, "end_line": 3}],
                    }
                ],
            }
        ],
    }
    original = REF + "\n\n```rich-content\n" + json.dumps(document, ensure_ascii=False) + "\n```"
    short = {
        "version": 1,
        "blocks": [
            {
                "id": "stop",
                "type": "step_flow",
                "steps": [
                    {
                        "id": "stop-flag",
                        "title": "停止",
                        "description": "保留前置条件与停止分支。",
                        "sources": [{"path": "Program.cs", "start_line": 1, "end_line": 3}],
                    }
                ],
            }
        ],
    }
    revised = "```rich-content\n" + json.dumps(short, ensure_ascii=False) + "\n```"
    text, events, sent = await compose(text=original, reply=revised)
    assert len(sent) == 1 and text == revised
    assert [block.type for _, _, doc in rich_documents(text) if doc for block in doc.blocks] == [
        "step_flow"
    ]
    assert "停止分支" in project_rich_content(text)
    assert events[-1][1]["changed"] is True


@pytest.mark.parametrize("language,version", [("json", 1), ("rich-content", 9)])
async def test_code_examples_and_unknown_protocol_do_not_skip_composer(language, version):
    text = LONG + f'\n\n```{language}\n{{"version":{version},"blocks":[]}}\n```'
    result, _, sent = await compose(text=text)
    assert result == SHORT
    assert len(sent) == 1
