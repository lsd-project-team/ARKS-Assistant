"""历史只做请求级投影，约束、近期轮次、工具链及原文回查保持完整。"""

import asyncio
import json

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.context.history_plan import HistoryPlan
from app.agents.context.history_selection import (
    ConversationHistorySelection,
    HistorySelectionUnavailable,
)
from app.agents.context.tokens import current_budget
from app.agents.runtime.engine import AgentRuntime
from app.agents.tools.conversation import conversation_tools
from app.core.config import AppSettings, ModelSettings
from app.modules.chat.context import ConversationContext
from tests.helpers.models import DeterministicModel

SUMMARY = (
    "You are in the middle of a conversation that has been summarized.\n<summary>\n"
    "## 目标\n未完成目标：解释方案并核对边界。\n"
    "## 用户要求与约束\n必须中文，只读，用户已纠正为版本2。\n"
    "## 已确认结论\n无关旧话题NOISE_A。\n本题需要的事实USEFUL_B。\n"
    "## 源码依据\n[相关](source:Program.cs#L1-L2)\n无关NOISE_C。\n"
    "## 待办\n尚未验证，不能声称完成。\n"
    "## 待确认项\n依赖未知，有冲突不能任选一方。\n</summary>"
)


def history(turns=8):
    rows = []
    for n in range(turns):
        rows.extend(
            [
                HumanMessage(content=f"用户要求{n}，只读，禁止修改。", id=f"user-{n}"),
                AIMessage(content=f"历史答复{n} OLD_FACT_{n}", id=f"answer-{n}"),
            ]
        )
    return rows


class Selector:
    def __init__(self, result=None):
        self.result, self.requests = result, []

    async def ainvoke(self, messages, **kwargs):
        self.requests.append(json.loads(messages[-1].text))
        if isinstance(self.result, BaseException):
            raise self.result
        result = self.result(self.requests[-1]) if callable(self.result) else self.result
        return AIMessage(
            content=result
            if isinstance(result, str)
            else json.dumps(result or {"carry_ids": [], "relevant_ids": []})
        )


async def project(messages, selector, **kwargs):
    events, received = [], []
    middleware = ConversationHistorySelection(
        selector,
        "继续解释这个方案",
        lambda *row: events.append(row),
        kwargs.pop("limit", 16000),
        **kwargs,
    )
    request = ModelRequest(
        model=DeterministicModel(),
        system_message=SystemMessage(content="系统规则"),
        messages=messages,
    )

    async def handler(prepared):
        received.append(prepared)
        return ModelResponse(result=[AIMessage(content="结果")])

    await middleware.awrap_model_call(request, handler)
    return middleware, events, received, request


async def test_short_dialogue_is_not_filtered_and_keeps_same_message_objects():
    messages = history(6)
    selector = Selector(AssertionError("短对话不应调用筛选模型"))
    _, events, received, request = await project(messages, selector)
    assert received[0] is request and not selector.requests and not events


async def test_current_user_message_quoting_a_summary_is_not_mistaken_for_native_history():
    current = HumanMessage(content=SUMMARY)
    selector = Selector(AssertionError("本轮原始问题不能被当成旧摘要筛选"))
    _, _, received, _ = await project([current], selector)
    assert received[0].messages[0] is current and not selector.requests


async def test_empty_summary_fact_sections_do_not_add_a_filter_call():
    summary = (
        "Here is a summary of the conversation to date:\n\n## 目标\n继续任务。\n"
        "## 已确认结论\n无\n## 源码依据\n无\n## 待办\n尚未完成。"
    )
    selector = Selector(AssertionError("没有事实候选时不增加筛选请求"))
    _, _, received, _ = await project(
        [HumanMessage(content=summary), HumanMessage(content="继续")], selector
    )
    assert "尚未完成" in received[0].messages[0].text and not selector.requests


async def test_older_answers_are_filtered_but_all_user_requirements_and_recent_six_turns_stay():
    messages = history()
    selector = Selector()
    middleware, events, received, request = await project(messages, selector)
    actual = received[0].messages
    assert [row.id for row in actual if row.type == "human"] == [f"user-{n}" for n in range(8)]
    assert [row.id for row in actual if row.type == "ai"] == [f"answer-{n}" for n in range(2, 8)]
    assert messages == request.messages and len(messages) == 16
    assert "最新要求" in received[0].system_message.text
    assert "用户要求7" in str(selector.requests[0]["recent"])
    assert "用户要求0" in str(selector.requests[0]["requirements"])
    assert events[-1][1]["after_tokens"] < events[-1][1]["before_tokens"]
    # 同一轮工具调用增加近期消息，不重复筛选旧历史。
    calls = []

    async def handler(prepared):
        calls.append(prepared)
        return ModelResponse(result=[AIMessage(content="结果")])

    changed = request.override(messages=[*messages, AIMessage(content="近期补充")])
    await middleware.awrap_model_call(changed, handler)
    assert len(selector.requests) == 1 and events[-1][1]["cached"] is True
    assert calls[0].messages[-1].text == "近期补充"


async def test_summary_keeps_goals_constraints_pending_and_conflicts_while_filtering_facts():
    original = HumanMessage(content=SUMMARY, id="summary")

    def choose(payload):
        return {
            "carry_ids": [],
            "relevant_ids": [
                row["id"]
                for row in payload["candidates"]
                if "USEFUL_B" in row.get("content", "") or "source:" in row.get("content", "")
            ],
        }

    _, _, received, _ = await project(
        [original, HumanMessage(content="这个方案呢")], Selector(choose)
    )
    result = received[0].messages[0].text
    for marker in ("未完成目标", "只读", "版本2", "尚未验证", "有冲突", "USEFUL_B", "source:"):
        assert marker in result
    assert "NOISE_" not in result
    assert original.text == SUMMARY and received[0].messages[0].id == "summary"


async def test_freeform_corrected_summary_is_protected_instead_of_losing_user_constraints():
    original = HumanMessage(
        content="Here is a summary of the conversation to date:\n\n纠正：只读，继续核对原目标。"
    )
    selector = Selector(AssertionError("自由格式纠正不能当作可丢弃事实"))
    _, _, received, _ = await project([original, HumanMessage(content="继续")], selector)
    assert received[0].messages[0] is original and not selector.requests


async def test_old_tool_calls_and_results_are_kept_or_removed_as_one_group():
    messages = history()
    call = AIMessage(
        content="",
        tool_calls=[{"id": "read", "name": "read_source", "args": {"path": "Program.cs"}}],
    )
    result = ToolMessage(content="OLD_TOOL_FACT", tool_call_id="read", name="read_source")
    messages[1:1] = [call, result]
    plan = HistoryPlan(messages)
    group = next(row for row in plan.candidates if "OLD_TOOL_FACT" in str(row))
    actual = plan.render({group["id"]})
    assert call in actual and result in actual
    assert call not in plan.render(set()) and result not in plan.render(set())
    assert plan.render({group["id"]})[1:4] == [call, result, messages[3]]


async def test_completed_or_cancelled_goal_status_can_be_carried_for_an_unrelated_question():
    messages = history()
    messages[1] = AIMessage(content="旧目标已完成，用户后来取消第二项。", id="status")

    def choose(payload):
        return {
            "carry_ids": [row["id"] for row in payload["candidates"] if "旧目标已完成" in str(row)],
            "relevant_ids": [],
        }

    _, _, received, _ = await project(messages, Selector(choose))
    plan = HistoryPlan(messages)
    candidate = next(row for row in plan.candidates if "旧目标已完成" in str(row))
    assert plan.protected[candidate["request_index"]]["content"] == messages[0].text
    assert "旧目标已完成" in str(received[0].messages) and "OLD_FACT_1" not in str(
        received[0].messages
    )


@pytest.mark.parametrize(
    "result",
    [
        "invalid",
        {"carry_ids": [True], "relevant_ids": []},
        {"carry_ids": [], "relevant_ids": [999]},
        {"carry_ids": [1, 1], "relevant_ids": []},
        RuntimeError("private-secret"),
    ],
)
async def test_invalid_or_failed_selection_never_sends_unscreened_history_to_answer_model(result):
    selector = Selector(result)
    messages = history()
    with pytest.raises(HistorySelectionUnavailable, match="原始消息和摘要均已保留") as caught:
        await project(messages, selector)
    assert "private-secret" not in str(caught.value)
    assert len(messages) == 16 and "OLD_FACT_0" in messages[1].text


async def test_input_budget_and_timeout_fail_explicitly_but_cancellation_propagates():
    selector = Selector(AssertionError("输入超限时不能调用供应商"))
    with pytest.raises(HistorySelectionUnavailable):
        await project(history(), selector, limit=1)
    assert selector.requests == []

    class Slow(Selector):
        async def ainvoke(self, *args, **kwargs):
            await asyncio.Event().wait()

    with pytest.raises(HistorySelectionUnavailable):
        await project(history(), Slow(), timeout=0.01)
    with pytest.raises(asyncio.CancelledError):
        await project(history(), Selector(asyncio.CancelledError()))


async def test_a_valid_item_in_both_categories_is_included_only_once():
    selector = Selector(
        lambda payload: {
            "carry_ids": [payload["candidates"][0]["id"]],
            "relevant_ids": [payload["candidates"][0]["id"]],
        }
    )
    _, _, received, _ = await project(history(), selector)
    ids = [row.id for row in received[0].messages]
    assert ids.count("answer-0") == 1 and "answer-1" not in ids


@pytest.mark.parametrize("second_batch_fails", [False, True])
async def test_history_batches_validate_global_ids_and_never_publish_partial_selection(
    second_batch_fails,
):
    from app.agents.context.history_selection import HISTORY_SELECTION_PROMPT
    from app.agents.context.tokens import estimate_tokens
    from app.core.config import dump_json

    messages = history()
    messages[1] = AIMessage(content="第一条背景" * 200)
    messages[3] = AIMessage(content="第二条背景" * 200)
    seen, received = [], []

    def choice(payload):
        seen.append(payload)
        if second_batch_fails and len(seen) == 2:
            raise RuntimeError("第二批处理失败")
        return {"carry_ids": [], "relevant_ids": [row["id"] for row in payload["candidates"]]}

    selector = ConversationHistorySelection(Selector(choice), "当前问题", lambda *_: None, 16000)
    plan = HistoryPlan(messages)
    selector.calls.input_limit = (
        max(
            estimate_tokens(
                [
                    SystemMessage(content=HISTORY_SELECTION_PROMPT),
                    HumanMessage(content=dump_json(selector.payload(plan, [candidate]))),
                ]
            )
            for candidate in plan.candidates
        )
        + 256
    )

    async def handler(request):
        received.append(request)
        return ModelResponse(result=[AIMessage(content="完成")])

    request = ModelRequest(model=DeterministicModel(), messages=messages)
    if second_batch_fails:
        with pytest.raises(HistorySelectionUnavailable):
            await selector.awrap_model_call(request, handler)
        assert received == [] and not selector.cache
    else:
        await selector.awrap_model_call(request, handler)
        assert received[0].messages == messages
    assert len(seen) == 2


async def test_edited_summary_and_latest_correction_invalidate_cached_selection():
    summary = HumanMessage(content=SUMMARY, id="summary")
    current = HumanMessage(content="最新纠正：目标改为核对方案C。", id="current")
    reviewer = Selector()
    middleware, _, _, request = await project([summary, current], reviewer)
    updated = summary.model_copy(update={"content": SUMMARY.replace("版本2", "版本3")})
    received = []

    async def handler(prepared):
        received.append(prepared)
        return ModelResponse(result=[AIMessage(content="完成")])

    await middleware.awrap_model_call(request.override(messages=[updated, current]), handler)
    assert len(reviewer.requests) == 2
    assert "版本3" in received[0].messages[0].text and received[0].messages[-1] is current


def test_filtered_budget_uses_actual_last_request_not_unfiltered_checkpoint_history():
    snapshot = {
        "tokens": 123,
        "breakdown": {"messages": 100, "system": 23},
        "history_filtered": True,
    }
    result = current_budget(history(), snapshot, 16000, 1000)
    assert result["tokens"] == 123 and result["breakdown"] == snapshot["breakdown"]
    assert result is not snapshot


async def test_real_agent_keeps_archives_and_recall_after_filtering_older_answers(
    services, monkeypatch
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(
            model=ModelSettings(context_tokens=32768, output_tokens=512),
            mcp_servers=[],
            auto_memory=False,
        )
    )
    selections, primary = [], []

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            if "你只负责选择回答需要的较早对话" in messages[0].text:
                selections.append(json.loads(messages[-1].text))
                answer = AIMessage(content='{"carry_ids":[],"relevant_ids":[]}')
            else:
                primary.append(messages)
                answer = AIMessage(content="近期方案继续核对，保持只读。")
            return ChatResult(generations=[ChatGeneration(message=answer)])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    options = {"use_memory": False, "use_knowledge": False, "use_deepwiki": False}
    thread = repository.create_thread("历史筛选")
    for n in range(8):
        run = repository.create_run(thread["id"], f"用户要求{n}，只读。", [], options)
        repository.finish(run["id"], f"历史事实OLD_FACT_{n}。")
    original = repository.thread(thread["id"])["messages"]
    run = repository.create_run(thread["id"], "继续这个方案", [], options)
    try:
        answer = await runtime.execute(
            run, lambda kind, row: repository.event(run["id"], kind, row)
        )
        repository.finish(run["id"], answer)
        assert len(selections) == 1 and len(primary) == 1
        context = "\n".join(row.text for row in primary[0])
        assert (
            "OLD_FACT_0" not in context
            and "OLD_FACT_1" not in context
            and "OLD_FACT_2" not in context
        )
        assert all(f"用户要求{n}" in context for n in range(8))
        assert all(f"OLD_FACT_{n}" in context for n in range(3, 8))
        assert repository.thread(thread["id"])["messages"][:16] == original
        tool = next(
            tool
            for tool in conversation_tools(repository, thread["id"])
            if tool.name == "read_conversation_message"
        )
        recovered = await tool.ainvoke({"message_id": original[1]["id"]})
        assert "OLD_FACT_0" in recovered
        restored = await ConversationContext(runtime).read(thread["id"])
        budget = repository.latest_event(thread["id"], "context_budget")
        assert restored["tokens"] == budget["tokens"] and budget["history_filtered"]
        assert not any(
            '"carry_ids"' in row["payload"].get("text", "")
            for row in repository.events(run["id"])
            if row["kind"] == "token"
        )
    finally:
        runtime.semantic.close()
