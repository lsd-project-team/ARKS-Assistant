"""阶段隔离、失败边界与终审事实保障；替身不承担真实语义评分。"""

import asyncio
import json

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.runtime.knowledge_answer import KnowledgeAnswerGuard
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


async def call(reviewer, text="本次记录216颗无刺穿。" + REF, records=RECORDS, limit=10000):
    events = []
    guard = KnowledgeAnswerGuard(
        reviewer, "总结试验", lambda: records, lambda *e: events.append(e), limit
    )

    async def handler(_request):
        return ModelResponse(
            result=[text if isinstance(text, AIMessage) else AIMessage(content=text)]
        )

    response = await guard.awrap_model_call(
        ModelRequest(model=DeterministicModel(), messages=[HumanMessage(content="总结试验")]),
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
