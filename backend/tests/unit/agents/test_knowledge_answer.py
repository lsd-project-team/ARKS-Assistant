"""阶段隔离、失败边界与终审事实保障；替身不承担真实语义评分。"""

import asyncio
import json

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.runtime.knowledge_answer import KnowledgeAnswerGuard
from app.modules.chat.rich_presentation import project_rich_content
from tests.helpers.models import DeterministicModel, fixture_selections

REF = "[试验 · v1](debug-issue:case/1)"
RECORDS = [{"reference": REF, "content": {"验证记录": "216颗无刺穿。"}}]
PASSED = {"verdict": "passed", "answer": ""}


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

    response = await guard.awrap_model_call(
        ModelRequest(model=DeterministicModel(), messages=[HumanMessage(content=question)]),
        handler,
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


async def test_real_fact_correction_gets_final_check_with_same_selected_source():
    revision = "本次216颗无刺穿，不能证明长期稳定。" + REF
    reviewer = Reviewer([{"verdict": "revised", "answer": revision}, PASSED])
    answer, events = await call(reviewer, "已长期量产稳定。" + REF)
    assert answer == revision
    facts = [
        payload for purpose, payload in reviewer.requests if purpose == "knowledge_verification"
    ]
    assert len(facts) == 2 and facts[-1]["final_check"]
    assert facts[0]["records"] == facts[1]["records"] == RECORDS
    assert all(
        '"answer"' not in str(payload)
        for kind, payload in events
        if kind == "knowledge_answer_check"
    )


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


async def test_selection_failure_is_processing_failure_not_missing_business_data():
    answer, events = await call(Reviewer(selection="not json"))
    assert "资料筛选暂未完成" in answer and "不代表资料库没有" in answer
    assert "216颗" not in answer and "debug-issue:" not in answer
    assert events[-2][1]["code"] == "invalid_structure"


async def test_valid_empty_selection_does_not_publish_candidate_or_claim_catalog_absence():
    answer, events = await call(Reviewer(selection={"selections": []}))
    assert "本轮返回的资料中" in answer and "无法据此确认" in answer
    assert "处理失败" not in answer and "216颗" not in answer and "debug-issue:" not in answer
    assert any(
        kind == "knowledge_answer_review" and row["references"] == [] for kind, row in events
    )


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
async def test_general_scope_does_not_bypass_review_when_answer_uses_experience(rich):
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
        Reviewer(selection={"scope": "general", "selections": []}),
        original,
        question="介绍Vue框架",
    )
    assert "没有选到" in answer and REF not in project_rich_content(answer)


async def test_reference_without_current_record_cannot_escape_review_as_no_sources():
    reviewer, checked = Reviewer(), []

    def missing(references):
        checked.append(references)
        return []

    answer, events = await call(reviewer, records=[], resolve=missing)
    assert checked == [{"debug-issue:case/1"}]
    assert "资料筛选暂未完成" in answer and REF not in answer and "216" not in answer
    assert reviewer.requests == []
    assert any(row.get("code") == "reference_unavailable" for _, row in events)


async def test_fact_provider_failure_keeps_only_preselected_time_fragment_and_error_code():
    target = "7月25日，23.2℃，精度-4~2μm。"
    records = [
        {"reference": REF, "content": {"正文": "7月23日，3μm。" + target + "7月27日，900μm。"}}
    ]
    reviewer = Reviewer(
        RuntimeError("credential-do-not-echo"),
        {"selections": [{"id": 1, "parts": [{"field": "正文", "start": 2, "end": 2}]}]},
    )
    answer, events = await call(reviewer, records=records)
    assert target in answer and "自动事实核查未完成" in answer
    assert "7月23日" not in answer and "900" not in answer
    assert "credential-do-not-echo" not in str(events)
    assert any(
        kind == "knowledge_stage_error" and row["code"] == "provider_error" for kind, row in events
    )


async def test_omitted_result_is_available_for_fact_check_without_reintroducing_other_records():
    original = "7月25日14:47开始，23.2℃。该阶段精度由-4~4μm变为-4~2μm。"
    records = [
        {"reference": REF, "content": {"正文": original}},
        {"reference": "[其他设备](debug-issue:other/1)", "content": {"正文": "adv-30，900μm。"}},
    ]
    revision = "该阶段范围由-4~4μm变为-4~2μm。" + REF
    reviewer = Reviewer(
        [{"verdict": "revised", "answer": revision}, PASSED],
        {"selections": [{"id": 1, "parts": [{"field": "正文", "start": 1, "end": 1}]}]},
    )
    answer, _ = await call(reviewer, "原记录没有提供精度。" + REF, records)
    assert answer == revision
    facts = [
        payload for purpose, payload in reviewer.requests if purpose == "knowledge_verification"
    ]
    assert len(facts) == 2
    for payload in facts:
        assert "-4~2" not in str(payload["records"])
        assert payload["record_context"] == records[:1]
        assert "900" not in str(payload)


async def test_repeated_wrong_facts_never_release_unverified_revision():
    reviewer = Reviewer({"verdict": "revised", "answer": "未经确认的新结论"})
    answer, events = await call(reviewer)
    assert "未经确认的新结论" not in answer and "216颗" in answer
    assert any(
        kind == "knowledge_stage_error" and row["code"] == "unresolved_facts"
        for kind, row in events
    )


async def test_foreign_reference_cannot_pass_merely_because_reviewer_says_passed():
    answer, _ = await call(Reviewer(), "无关900μm。[其他](debug-issue:other/1)")
    assert "900" not in answer and "other/1" not in answer
    assert "216颗" in answer


@pytest.mark.parametrize("records,limit", [([], 10000), (RECORDS, 1)])
async def test_no_records_or_input_budget_never_calls_provider(records, limit):
    reviewer = Reviewer(AssertionError("不应请求供应商"))
    answer, events = await call(reviewer, records=records, limit=limit)
    assert reviewer.requests == []
    if records:
        assert "处理失败" in answer and any(row.get("code") == "input_budget" for _, row in events)
    else:
        assert "216颗" in answer and events == []


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
async def test_code_examples_or_invalid_rich_content_do_not_bypass_knowledge_review(fake_source):
    reviewer = Reviewer(selection={"selections": []})
    answer, _ = await call(reviewer, "候选记录。\n\n" + fake_source)
    assert "没有选到" in answer
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


async def test_unselected_knowledge_reference_inside_rich_text_is_still_rejected():
    document = {
        "version": 1,
        "blocks": [{"id": "text", "type": "text", "content": "其他记录。" + REF}],
    }
    text = RICH_SOURCE + "\n```rich-content\n" + json.dumps(document) + "\n```"
    reviewer = Reviewer(selection={"selections": []})
    answer, _ = await call(reviewer, text)
    assert REF not in project_rich_content(answer)
    assert "资料筛选暂未完成" in answer
    assert [purpose for purpose, _ in reviewer.requests] == [
        "knowledge_selection",
        "knowledge_verification",
        "knowledge_verification",
    ]


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
    assert "没有选到" in answer and "216颗" not in answer
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


async def test_visuals_do_not_bypass_unresolved_fact_fallback():
    original = (
        '```rich-content\n{"version":1,"blocks":[{"id":"bad","type":"mermaid",'
        '"content":"flowchart TD\\n A[075顶针] --> B[保证长期根治]"}]}\n```\n' + REF
    )
    answer, events = await call(
        Reviewer({"verdict": "revised", "answer": original}),
        original,
        question="用流程图展示经验",
    )
    assert "保证长期根治" not in answer and "216颗无刺穿" in answer
    assert any(
        kind == "knowledge_stage_error" and row["code"] == "unresolved_facts"
        for kind, row in events
    )
