"""阶段隔离、失败边界与终审事实保障；替身不承担真实语义评分。"""

import asyncio
import json

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.runtime.answer_review import AnswerReviewNote
from app.agents.runtime.knowledge_answer import KnowledgeAnswerGuard
from app.modules.chat.rich_presentation import project_rich_content
from tests.helpers.models import DeterministicModel, fixture_selections

REF = "[试验 · v1](debug-issue:case/1)"
RECORDS = [{"reference": REF, "content": {"验证记录": "216颗无刺穿。"}}]
PASSED = {"verdict": "passed", "note": ""}


class Reviewer:
    def __init__(self, facts=PASSED, selection=None):
        self.facts, self.selection, self.requests = facts, selection, []

    async def ainvoke(self, messages, **kwargs):
        payload = json.loads(messages[-1].text)
        purpose = kwargs["config"]["metadata"]["lc_source"]
        self.requests.append((purpose, payload))
        value = self.selection if purpose == "knowledge_selection" else self.facts
        if purpose == "knowledge_selection" and value is None:
            value = {"selections": fixture_selections(payload["records"])}
        if isinstance(value, list):
            value = value.pop(0)
        if isinstance(value, BaseException):
            raise value
        return AIMessage(content=value if isinstance(value, str) else json.dumps(value))


async def call(
    reviewer,
    text="本次记录216颗无刺穿。" + REF,
    records=RECORDS,
    limit=10000,
    *,
    question="总结试验",
    source_required=False,
    resolve=None,
):
    events = []
    guard = KnowledgeAnswerGuard(
        reviewer,
        question,
        lambda: records,
        lambda *e: events.append(e),
        limit,
        source_required=source_required,
        resolve=resolve,
    )

    async def handler(_request):
        return ModelResponse(
            result=[text if isinstance(text, AIMessage) else AIMessage(content=text)]
        )

    async def checked(request):
        return await guard.awrap_model_call(request, handler)

    response = await AnswerReviewNote().awrap_model_call(
        ModelRequest(model=DeterministicModel(), messages=[HumanMessage(content=question)]), checked
    )
    return response.result[0].text, events


async def test_selection_does_not_see_draft_and_fact_check_cannot_reselect_or_format():
    reviewer = Reviewer()
    text = "**" + "本次记录216颗无刺穿。" * 6 + "**" + REF
    answer, events = await call(reviewer, text)
    assert answer == text
    assert [purpose for purpose, _ in reviewer.requests] == [
        "knowledge_selection",
        "knowledge_verification",
    ]
    selection, facts = [payload for _, payload in reviewer.requests]
    assert "answer" not in selection
    assert facts["records"] == RECORDS
    assert "must_rewrite" not in facts and "selections" not in facts
    assert events[-1][1]["verdict"] == "passed"


async def test_fact_issue_adds_one_note_without_rewriting_or_second_check():
    original = "已长期量产稳定。" + REF
    note = "216颗的记录结果不能证明长期量产稳定。"
    reviewer = Reviewer({"verdict": "issues", "note": note, "answer": "不能采用的修订全文"})
    answer, events = await call(reviewer, original)
    assert answer == original + "\n\n" + note
    assert "不能采用的修订全文" not in answer
    facts = [
        payload for purpose, payload in reviewer.requests if purpose == "knowledge_verification"
    ]
    assert len(facts) == 1 and "final_check" not in facts[0]
    assert facts[0]["answer"] == original
    assert events[-1][1]["verdict"] == "issues"


async def test_bad_selection_schema_is_repaired_before_any_fact_check():
    reviewer = Reviewer(
        selection=[
            {"selections": [{"id": 999, "parts": []}]},
            {"selections": [{"id": 1, "parts": [{"field": "验证记录", "start": 1, "end": 1}]}]},
        ]
    )
    answer, _ = await call(reviewer)
    assert "216颗" in answer and "失败" not in answer
    assert [p for p, _ in reviewer.requests] == [
        "knowledge_selection",
        "knowledge_selection",
        "knowledge_verification",
    ]
    assert reviewer.requests[1][1]["protocol_hint"]


@pytest.mark.parametrize("bad", ["", "invalid json", "[]", '{"verdict":"revised","answer":""}'])
async def test_invalid_fact_protocol_can_recover_without_reselecting(bad):
    reviewer = Reviewer([bad, PASSED])
    answer, events = await call(reviewer)
    assert answer.startswith("本次记录")
    assert sum(p == "knowledge_selection" for p, _ in reviewer.requests) == 1
    assert any(kind == "knowledge_stage_error" for kind, _ in events)


async def test_selection_failure_preserves_original_and_only_records_processing_error():
    original = "本次记录216颗无刺穿。" + REF
    answer, events = await call(Reviewer(selection="not json"))
    assert answer == original
    assert events[-1][1]["verdict"] == "unknown"
    assert events[-2][1]["code"] == "invalid_structure"


async def test_empty_selection_adds_support_gap_without_rewriting_original():
    original = "本次记录216颗无刺穿。" + REF
    reviewer = Reviewer(selection={"selections": []})
    answer, events = await call(reviewer)
    assert answer == original + "\n\n本轮没有选到能支撑该历史答案的经验记录。"
    assert all(purpose != "knowledge_verification" for purpose, _ in reviewer.requests)
    assert events[-1][1]["verdict"] == "issues"


@pytest.mark.parametrize(
    "question,original",
    [
        ("你好", "你好！有什么可以帮你？"),
        (
            "给我介绍一下vue框架",
            "Vue 是用于构建用户界面的 JavaScript 框架，支持组件化和响应式更新。",
        ),
        ("解释一下HTTP和WebSocket的区别", "HTTP 常用于请求与响应，WebSocket 支持双向持续通信。"),
        ("把这句话翻译成英文：早上好", "Good morning."),
    ],
)
async def test_general_question_is_not_replaced_when_unrelated_records_select_nothing(
    question, original
):
    reviewer = Reviewer(selection={"scope": "general", "selections": []})
    answer, events = await call(reviewer, original, question=question)
    assert answer == original
    assert [purpose for purpose, _ in reviewer.requests] == ["knowledge_selection"]
    assert "answer" not in reviewer.requests[0][1]
    assert not any(kind == "answer_replace" for kind, _ in events)
    assert events[-1][1]["verdict"] == "skipped"


@pytest.mark.parametrize("rich", [False, True])
async def test_general_scope_does_not_hide_unsupported_experience_or_rewrite_it(rich):
    original = "通用介绍中夹带未经核查的记录。" + REF
    if rich:
        original = (
            "```rich-content\n"
            + json.dumps(
                {"version": 1, "blocks": [{"id": "t", "type": "text", "content": original}]}
            )
            + "\n```"
        )
    answer, _ = await call(
        Reviewer(selection={"scope": "general", "selections": []}), original, question="介绍Vue框架"
    )
    assert answer == original + "\n\n本轮没有选到能支撑该历史答案的经验记录。"
    assert REF in project_rich_content(answer)


async def test_missing_reference_adds_one_note_without_changing_original():
    reviewer, checked = Reviewer(), []

    def missing(references):
        checked.append(references)
        return []

    original = "本次记录216颗无刺穿。" + REF
    answer, events = await call(reviewer, records=[], resolve=missing)
    assert checked == [{"debug-issue:case/1"}]
    assert answer == original + "\n\n回答中的经验引用未在本轮可用记录中找到。"
    assert reviewer.requests == [] and events[-1][1]["verdict"] == "issues"


async def test_fact_provider_failure_preserves_draft_and_keeps_error_out_of_body():
    target = "7月25日，23.2℃，精度-4~2μm。"
    records = [
        {"reference": REF, "content": {"正文": "7月23日，3μm。" + target + "7月27日，900μm。"}}
    ]
    reviewer = Reviewer(
        RuntimeError("credential-do-not-echo"),
        {"selections": [{"id": 1, "parts": [{"field": "正文", "start": 2, "end": 2}]}]},
    )
    original = "本次记录216颗无刺穿。" + REF
    answer, events = await call(reviewer, records=records)
    assert answer == original
    assert "credential-do-not-echo" not in str(events)
    facts = [p for purpose, p in reviewer.requests if purpose == "knowledge_verification"]
    assert len(facts) == 1 and facts[0]["records"][0]["content"] == {"正文": target}
    assert any(k == "knowledge_stage_error" and r["code"] == "provider_error" for k, r in events)


async def test_full_record_supports_specific_note_without_reintroducing_other_records():
    evidence = "7月25日14:47开始，23.2℃。该阶段精度由-4~4μm变为-4~2μm。"
    records = [
        {"reference": REF, "content": {"正文": evidence}},
        {"reference": "[其他设备](debug-issue:other/1)", "content": {"正文": "adv-30，900μm。"}},
    ]
    note = "原记录给出了精度由-4~4μm变为-4~2μm的结果。"
    reviewer = Reviewer(
        {"verdict": "issues", "note": note},
        {"selections": [{"id": 1, "parts": [{"field": "正文", "start": 1, "end": 1}]}]},
    )
    original = "原记录没有提供精度。" + REF
    answer, _ = await call(reviewer, original, records)
    assert answer == original + "\n\n" + note
    facts = [p for purpose, p in reviewer.requests if purpose == "knowledge_verification"]
    assert len(facts) == 1
    assert "-4~2" not in str(facts[0]["records"])
    assert facts[0]["record_context"] == records[:1] and "900" not in str(facts[0])


async def test_review_never_uses_returned_replacement_or_retries_to_rewrite():
    original = "本次记录216颗无刺穿。" + REF
    note = "该记录只有216颗样本。"
    reviewer = Reviewer({"verdict": "issues", "note": note, "answer": "未经确认的新结论"})
    answer, events = await call(reviewer)
    assert answer == original + "\n\n" + note and "未经确认的新结论" not in answer
    assert sum(p == "knowledge_verification" for p, _ in reviewer.requests) == 1
    assert not any(k == "answer_replace" for k, _ in events)


async def test_foreign_reference_is_reported_even_when_model_says_passed():
    original = "无关900μm。[其他](debug-issue:other/1)"
    answer, events = await call(Reviewer(), original)
    assert answer == original + "\n\n回答中的经验引用与本轮选定记录或版本不一致。"
    assert events[-1][1]["verdict"] == "issues"


@pytest.mark.parametrize("records,limit", [([], 10000), (RECORDS, 1)])
async def test_no_records_or_input_budget_never_calls_provider_or_rewrites(records, limit):
    reviewer = Reviewer(AssertionError("不应请求供应商"))
    original = "本次记录216颗无刺穿。" + REF
    answer, events = await call(reviewer, records=records, limit=limit)
    assert reviewer.requests == [] and answer == original
    if records:
        assert any(r.get("code") == "input_budget" for _, r in events)
    else:
        assert events == []


async def test_cancellation_is_not_swallowed_as_review_failure():
    with pytest.raises(asyncio.CancelledError):
        await call(Reviewer(selection=asyncio.CancelledError()))


@pytest.mark.parametrize("output", ["incomplete", "suspected_truncated"])
async def test_incomplete_answer_does_not_enter_selection_or_fact_check(output):
    reviewer = Reviewer(selection=AssertionError("不能核查半段回答"))
    text = AIMessage(content="半段", additional_kwargs={"answer_completion": {"output": output}})
    answer, events = await call(reviewer, text)
    assert answer == "半段" and reviewer.requests == [] and events == []


async def test_tool_call_response_is_left_to_tools_instead_of_reviewed_as_answer():
    reviewer = Reviewer(selection=AssertionError("工具调用不是最终回答"))
    message = AIMessage(
        content="", tool_calls=[{"id": "read", "name": "read_debug_issue", "args": {}}]
    )
    answer, events = await call(reviewer, message)
    assert answer == "" and events == [] and reviewer.requests == []


SOURCE = "[源码](source:Program.cs#L1-L3)"
RICH_SOURCE = (
    '```rich-content\n{"version":1,"blocks":[{"id":"s","type":"step_flow",'
    '"steps":[{"id":"one","title":"入口","description":"保存参数",'
    '"sources":[{"path":"Program.cs","start_line":1,"end_line":3}]}]}]}\n```'
)


@pytest.mark.parametrize("text", ["准备标定。" + SOURCE, RICH_SOURCE])
@pytest.mark.parametrize("selection", [{"selections": []}, "not json", RuntimeError("secret")])
async def test_source_answer_is_not_replaced_by_unrelated_knowledge_or_selection_failure(
    text, selection
):
    reviewer = Reviewer(selection=selection)
    answer, events = await call(reviewer, text)
    assert answer == text and reviewer.requests == []
    assert events == [
        (
            "knowledge_answer_review",
            {"verdict": "skipped", "reason": "源码回答由源码核查处理", "references": []},
        )
    ]


@pytest.mark.parametrize(
    "fake_source",
    [
        "source:Program.cs#L1-L3",
        "`" + SOURCE + "`",
        "```text\n" + SOURCE + "\n```",
        RICH_SOURCE.replace('"version":1', '"version":9'),
    ],
)
async def test_code_examples_do_not_hide_support_gap_or_get_rewritten(fake_source):
    original = "候选记录。\n\n" + fake_source
    reviewer = Reviewer(selection={"selections": []})
    answer, _ = await call(reviewer, original)
    assert answer == original + "\n\n本轮没有选到能支撑该历史答案的经验记录。"
    assert [purpose for purpose, _ in reviewer.requests] == ["knowledge_selection"]


@pytest.mark.parametrize("source", [SOURCE, RICH_SOURCE])
async def test_mixed_source_and_knowledge_answer_still_receives_fact_review(source):
    text = source + "\n\n本次记录216颗无刺穿。" + REF
    reviewer = Reviewer()
    answer, _ = await call(reviewer, text, source_required=True, question="设备标定流程及历史经验")
    assert answer == text
    assert [purpose for purpose, _ in reviewer.requests] == [
        "knowledge_selection",
        "knowledge_verification",
    ]


async def test_unselected_reference_in_rich_text_is_reported_without_removing_blocks():
    document = {
        "version": 1,
        "blocks": [{"id": "text", "type": "text", "content": "其他记录。" + REF}],
    }
    original = RICH_SOURCE + "\n```rich-content\n" + json.dumps(document) + "\n```"
    reviewer = Reviewer(selection={"selections": []})
    answer, _ = await call(reviewer, original)
    assert answer == original + "\n\n本轮没有选到能支撑该历史答案的经验记录。"
    assert REF in project_rich_content(answer)
    assert [p for p, _ in reviewer.requests] == ["knowledge_selection"]


@pytest.mark.parametrize(
    "text",
    [
        "本轮源码流程草稿尚缺引用。",
        RICH_SOURCE.replace(
            '"sources":[{"path":"Program.cs","start_line":1,"end_line":3}]', '"sources":[]'
        ),
    ],
)
@pytest.mark.parametrize("selection", [{"selections": []}, "not json", RuntimeError("secret")])
async def test_source_task_missing_citations_is_left_to_source_guard_instead_of_empty_knowledge(
    text, selection
):
    reviewer = Reviewer(selection=selection)
    answer, events = await call(
        reviewer, text, source_required=True, question="我想在做设备标定，给我输出一下标定流程"
    )
    assert answer == text and reviewer.requests == []
    assert events[-1][1]["verdict"] == "skipped"


@pytest.mark.parametrize(
    "question",
    [
        "给我设备标定流程的历史记录原文",
        "查一下标定经验",
        "展示记录文字和原图",
    ],
)
async def test_explicit_historical_request_is_not_exempted_by_source_requirement(question):
    reviewer = Reviewer(selection={"selections": []})
    answer, _ = await call(reviewer, source_required=True, question=question)
    assert answer.startswith("本次记录216颗无刺穿。" + REF) and "没有选到" in answer
    assert [purpose for purpose, _ in reviewer.requests] == ["knowledge_selection"]


@pytest.mark.parametrize("question", ["给出 Program.cs 原文", "逐字输出设备标定流程源码"])
async def test_source_verbatim_request_is_not_misclassified_as_historical_material(question):
    reviewer = Reviewer(selection={"selections": []})
    original = "代码原文待补齐引用。"
    answer, _ = await call(reviewer, original, source_required=True, question=question)
    assert answer == original and reviewer.requests == []


@pytest.mark.parametrize(
    "block",
    [
        {
            "id": "flow",
            "type": "mermaid",
            "content": "flowchart TD\n A[组合调整] --> B[216颗无刺穿]",
        },
        {
            "id": "map",
            "type": "mindmap",
            "nodes": [
                {"id": "root", "label": "本次试验"},
                {"id": "result", "label": "216颗", "parent_id": "root"},
            ],
        },
        {
            "id": "chart",
            "type": "chart",
            "chart_type": "bar",
            "labels": ["本次取放颗数"],
            "series": [{"id": "count", "name": "数量", "values": [216]}],
        },
    ],
)
async def test_no_original_images_does_not_remove_verified_visuals_or_their_ids(block):
    records = [{**RECORDS[0], "image_count": 0}]
    original = (
        "本次记录216颗无刺穿，不代表长期验证。"
        + REF
        + "\n\n```rich-content\n"
        + json.dumps({"version": 1, "blocks": [block]})
        + "\n```"
    )
    reviewer = Reviewer()
    answer, events = await call(reviewer, original, records, question="用图文并茂说明本次试验")
    assert answer == original
    assert reviewer.requests[-1][1]["record_context"][0]["image_count"] == 0
    assert reviewer.requests[-1][1]["answer"] == original
    assert reviewer.requests[-1][1]["answer_text"] == project_rich_content(original)
    assert "216" in reviewer.requests[-1][1]["answer_text"]
    assert not any(kind == "answer_replace" for kind, _ in events)
    assert events[-1][1]["verdict"] == "passed"


async def test_visual_issue_adds_note_without_rewriting_graph():
    original = (
        '```rich-content\n{"version":1,"blocks":[{"id":"bad","type":"mermaid",'
        '"content":"flowchart TD\\n A[075顶针] --> B[保证长期根治]"}]}\n```\n' + REF
    )
    note = "216颗样本不能证明保证长期根治。"
    reviewer = Reviewer({"verdict": "issues", "note": note, "answer": "不应采用的图形修订"})
    answer, _ = await call(reviewer, original, question="用流程图展示经验")
    assert answer == original + "\n\n" + note
    assert "保证长期根治" in answer and "不应采用的图形修订" not in answer
    assert sum(p == "knowledge_verification" for p, _ in reviewer.requests) == 1
