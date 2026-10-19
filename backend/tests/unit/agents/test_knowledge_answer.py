import asyncio
import json

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.runtime.knowledge_answer import (
    KnowledgeAnswerGuard,
    answer_problems,
    topic_needs_synthesis,
)
from tests.helpers.models import DeterministicModel

RECORDS = [{"reference": "[试验 · v1](debug-issue:case/1)", "content": {"验证记录": "216颗无刺穿"}}]


class Reviewer:
    def __init__(self, content):
        self.content, self.requests = content, []

    async def ainvoke(self, messages, **kwargs):
        self.requests.append((messages, kwargs))
        content = self.content.pop(0) if isinstance(self.content, list) else self.content
        if isinstance(content, BaseException):
            raise content
        return AIMessage(content=content)


async def call_guard(reviewer, answer, records=RECORDS, limit=10000, question="总结这次试验"):
    events = []
    guard = KnowledgeAnswerGuard(
        reviewer, question, lambda: records, lambda *event: events.append(event), limit
    )

    async def handler(_request):
        return ModelResponse(result=[answer])

    result = await guard.awrap_model_call(
        ModelRequest(model=DeterministicModel(), messages=[HumanMessage(content=question)]),
        handler,
    )
    return result.result[0], events


async def test_review_revises_overclaim_and_emits_only_final_text():
    revision = "本次记录显示216颗无刺穿，不能证明长期根治。[试验 · v1](debug-issue:case/1)"
    reviewer = Reviewer(
        [
            json.dumps({"verdict": "revised", "reason": "过度推广", "answer": revision}),
            '{"verdict":"passed","reason":"修订未扩大事实","answer":""}',
        ]
    )
    answer, events = await call_guard(reviewer, AIMessage(content="所有工况都能根治。"))
    assert answer.text == revision
    assert [payload["text"] for kind, payload in events if kind == "answer_replace"] == [revision]
    assert events[-1][1]["verdict"] == "revised"
    messages, kwargs = reviewer.requests[0]
    assert json.loads(messages[-1].text)["records"] == RECORDS
    assert kwargs["config"]["metadata"]["lc_source"] == "knowledge_verification"
    assert [payload["purpose"] for kind, payload in events if kind == "provider_usage"] == [
        "knowledge_verification",
        "knowledge_verification",
    ]


async def test_passed_review_preserves_answer_and_verbatim_request():
    reviewer = Reviewer('{"verdict":"passed","reason":"引文忠实","answer":""}')
    raw = "【经验】原记录认为可以根治。"
    answer, events = await call_guard(reviewer, AIMessage(content=raw), question="请逐字引用原文")
    assert answer.text == raw
    assert not any(kind == "answer_replace" for kind, _ in events)
    assert events[-1][1]["verdict"] == "passed"


async def test_repeated_unverified_revisions_fall_back_to_attributed_source():
    reviewer = Reviewer('{"verdict":"revised","reason":"仍有臆测","answer":"仍有臆测的新稿"}')
    answer, events = await call_guard(reviewer, AIMessage(content="原先的错误分析"))
    assert len(reviewer.requests) == 2
    assert "本轮分析尚未通过复核" in answer.text
    assert "216颗无刺穿" in answer.text and "debug-issue:case/1" in answer.text
    assert "仍有臆测的新稿" not in answer.text
    assert any(
        kind == "knowledge_answer_review" and row["verdict"] == "unknown" for kind, row in events
    )


async def test_passed_verdict_does_not_bypass_detected_record_card():
    reviewer = Reviewer('{"verdict":"passed","answer":""}')
    answer, _events = await call_guard(
        reviewer, AIMessage(content="**问题**：现象\n**结果**：216颗"), question="试验经验"
    )
    assert len(reviewer.requests) == 2
    assert json.loads(reviewer.requests[0][0][-1].text)["must_rewrite"]
    assert "本轮分析尚未通过复核" in answer.text


@pytest.mark.parametrize("records,limit", [([], 10000), (RECORDS, 1)])
async def test_no_evidence_or_budget_does_not_call_reviewer(records, limit):
    reviewer = Reviewer(AssertionError("不应调用供应商"))
    answer, events = await call_guard(reviewer, AIMessage(content="原回答"), records, limit)
    assert reviewer.requests == []
    if records:
        assert "本轮分析尚未通过复核" in answer.text
        assert any(kind == "notice" for kind, _ in events)
    else:
        assert answer.text == "原回答"
        assert events == []


@pytest.mark.parametrize("output", ["incomplete", "suspected_truncated"])
async def test_incomplete_answer_is_not_rewritten(output):
    reviewer = Reviewer(AssertionError("不应复核半段回答"))
    answer = AIMessage(content="半段", additional_kwargs={"answer_completion": {"output": output}})
    result, events = await call_guard(reviewer, answer)
    assert result.text == "半段" and reviewer.requests == [] and events == []


@pytest.mark.parametrize(
    "result",
    ["not json", '{"verdict":"revised","answer":" "}', RuntimeError("credential-do-not-echo")],
)
async def test_review_failure_returns_attributed_source_without_leaking_error(result):
    answer, events = await call_guard(Reviewer(result), AIMessage(content="原回答"))
    assert "本轮分析尚未通过复核" in answer.text
    assert "216颗无刺穿" in answer.text and "原回答" not in answer.text
    assert any(kind == "notice" for kind, _ in events)
    assert "credential-do-not-echo" not in str(events)
    assert any(
        kind == "knowledge_answer_review" and row["verdict"] == "unknown" for kind, row in events
    )


async def test_cancellation_propagates():
    with pytest.raises(asyncio.CancelledError):
        await call_guard(Reviewer(asyncio.CancelledError()), AIMessage(content="原回答"))


async def test_fallback_masks_credentials_without_changing_original_record():
    records = [
        {
            "reference": RECORDS[0]["reference"],
            "content": {"记录正文": "api_key='do-not-leak'\n216颗无刺穿"},
        }
    ]
    answer, _events = await call_guard(Reviewer("invalid"), AIMessage(content="分析草稿"), records)
    assert "do-not-leak" not in answer.text and "[敏感值已隐藏]" in answer.text
    assert "do-not-leak" in records[0]["content"]["记录正文"]
    assert "原文较长" not in answer.text


@pytest.mark.parametrize(
    "question,expected",
    [
        ("试验经验", True),
        ("请列出处理步骤", False),
        ("请逐字引用原文", False),
        ("分析并给建议", False),
    ],
)
def test_record_card_detection_respects_explicit_output_request(question, expected):
    assert topic_needs_synthesis(question, "**问题**：现象\n**结果**：216颗") is expected


@pytest.mark.parametrize(
    "answer",
    [
        "本次组合有试验依据。\n\n### 调整参数\n- 顶针：075\n\n### 复用建议\n先核对条件。",
        "本次组合有试验依据。\n\n**本次参数**\n- **顶针**：075\n"
        "- **焊头力**：20~30g\n- **速度**：3mm/s\n\n**适用范围**\n仅限记录条件。",
        "结果显示216颗无刺穿。\n\n经验需要结合本次条件理解。",
        "本次组合有试验依据，复用仍需核对条件。\n\n**方案**\n- 顶针：075"
        "\n\n**结果**\n216颗无刺穿。",
    ],
)
def test_readable_headings_and_parameter_lists_are_not_record_cards(answer):
    assert not topic_needs_synthesis("蓝膜刺穿处理经验", answer)
    assert not answer_problems("蓝膜刺穿处理经验", answer)


async def test_review_preserves_readable_structure_without_forcing_prose():
    text = "本次组合后216颗无刺穿。\n\n### 如何复用\n先核对条件。\n\n### 适用范围\n不能直接推广。"
    reviewer = Reviewer('{"verdict":"passed","answer":""}')
    answer, events = await call_guard(reviewer, AIMessage(content=text), question="试验经验")
    assert answer.text == text
    assert len(reviewer.requests) == 1
    assert not json.loads(reviewer.requests[0][0][-1].text)["must_rewrite"]
    assert not any(kind == "answer_replace" for kind, _ in events)


@pytest.mark.parametrize(
    "answer",
    [
        "### 问题\n现象\n\n### 方案\n处理\n\n### 结果\n216颗",
        "- **问题：**现象\n- **处理办法：**处理\n- **验证记录：**216颗",
        "【问题】现象\n【方案】处理\n【结果】216颗",
    ],
)
def test_source_field_cards_are_detected_across_markdown_styles(answer):
    assert topic_needs_synthesis("试验经验", answer)


def test_returned_records_do_not_prove_whole_catalog_absence():
    assert answer_problems("其他尺寸也一样吗？", "库里没有其他规格的数据。")
    assert not answer_problems("其他尺寸也一样吗？", "这份记录未提供其他规格的数据。")
    assert not answer_problems("请逐字引用原文", "库里没有其他规格的数据。")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("**" + "本次观察结果仅限该组合与条件" * 4 + "**", "大块加粗"),
        ("参数A：1 + 参数B：2 + 参数C：3 + 参数D：4", "逐项参数列表"),
        ("本次记录说明的范围有限。" * 18, "连续正文段"),
    ],
)
def test_observed_readability_problems_are_sent_to_reviewer(text, expected):
    assert expected in answer_problems("试验经验", text)
    assert not answer_problems("请提取完整原文", text)
    assert not answer_problems("请保持格式", text)


def test_readability_checks_preserve_lists_code_and_quotes():
    text = "- 参数A：1\n- 参数B：2\n- 参数C：3\n- 参数D：4\n\n**关键结果**：成功。"
    assert not answer_problems("试验经验", text)
    literal = "**" + "引文内容" * 20 + "** + 1 + 2 + 3"
    assert not answer_problems("试验经验", f"```text\n{literal}\n```")
    assert not answer_problems("试验经验", "> " + literal)
    table = "| 参数 | 值 |\n| --- | --- |\n" + "| 验证数量 | 216颗 |\n" * 20
    assert not answer_problems("请用表格列出记录", table)


async def test_passed_review_cannot_ignore_explicit_readability_problem():
    reviewer = Reviewer('{"verdict":"passed","answer":""}')
    answer, _events = await call_guard(
        reviewer, AIMessage(content="参数A：1 + 参数B：2 + 参数C：3 + 参数D：4")
    )
    assert len(reviewer.requests) == 2
    assert "逐项参数列表" in json.loads(reviewer.requests[0][0][-1].text)["must_rewrite"]
    assert "本轮分析尚未通过复核" in answer.text
