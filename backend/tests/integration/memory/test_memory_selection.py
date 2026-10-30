"""第二阶段适用性复核：真实记忆与快照，供应商响应使用可控替身。"""

import asyncio
import inspect
import json

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.context.tokens import estimate_tokens, input_budget
from app.agents.runtime.engine import AgentRuntime
from app.agents.runtime.model_budget import ProjectModelBudget
from app.core.config import ModelSettings
from app.modules.auth.context import request_identity
from app.modules.chat.models import Message, Thread
from app.modules.knowledge.search import catalog
from app.modules.memory.selection import MemorySelection
from app.modules.settings.model_ledger import ModelLedger
from tests.helpers.memories import MemorySeed, seed_memory
from tests.helpers.models import DeterministicModel


class Picker:
    def __init__(self, choose):
        self.choose, self.calls = choose, []

    async def ainvoke(self, messages, **kwargs):
        payload = json.loads(messages[-1].text)
        self.calls.append((messages, kwargs))
        value = self.choose(payload)
        if inspect.isawaitable(value):
            value = await value
        return AIMessage(
            content=value if isinstance(value, str) else json.dumps(value),
            usage_metadata={"input_tokens": 50, "output_tokens": 5, "total_tokens": 55},
        )


@pytest.fixture
def remembered(services, monkeypatch):
    memory = services[4]
    monkeypatch.setattr(catalog(services[1]).retrieval, "scores", lambda *_: {})
    seed_memory(
        memory,
        MemorySeed(
            "ZX2200真空V2", "ZX2200 V2真空标定前必须确认负压已经释放。", source_paths=["Program.cs"]
        ),
    )
    seed_memory(
        memory, MemorySeed("旧机真空V1", "旧机V1真空标定使用另一套参数，不能套用到ZX2200 V2。")
    )
    query = "ZX2200 V2真空标定有哪些前提"
    candidates = memory.candidates(query)
    assert len(candidates["matches"]) == 2
    return memory, query, candidates


def run_gate(memory, query, model, *, settings=None, max_tokens=8000):
    events = []
    gate = MemorySelection(
        memory, model, settings or ModelSettings(), lambda kind, row: events.append((kind, row))
    )
    return gate.prepare(query, max_tokens=max_tokens), events


async def test_only_model_approved_ids_reach_answer_snapshot_without_rewriting(remembered):
    memory, query, candidates = remembered
    original = memory.list()
    wanted = next(
        fact["id"] for _, fact in candidates["matches"] if fact["title"] == "ZX2200真空V2"
    )
    model = Picker(lambda _payload: {"memory_ids": [wanted]})
    invocation, events = run_gate(memory, query, model)
    prompt, rows = await invocation
    payload = json.loads(model.calls[0][0][-1].text)
    assert payload["question"] == query and len(payload["candidates"]) == 2
    assert all(row["evidence"] and row["content"] for row in payload["candidates"])
    assert model.calls[0][1]["max_tokens"] == 512
    assert "必须确认负压已经释放。" in prompt and "另一套参数" not in prompt
    assert rows[0]["memory_ids"] == [wanted] and "模型复核" in rows[0]["inclusion_reason"]
    assert rows[0]["content"] in prompt and rows[0]["injected_text"] == prompt
    assert memory.list() == original
    usage = next(row for kind, row in events if kind == "provider_usage")
    assert usage["purpose"] == "memory_selection" and usage["total_tokens"] == 55


async def test_model_may_reject_all_lexical_matches(remembered):
    memory, query, _ = remembered
    invocation, events = run_gate(memory, query, Picker(lambda _: {"memory_ids": []}))
    assert await invocation == ("", [])
    assert events[-1][1]["status"] == "none" and memory.list()


@pytest.mark.parametrize("kind", ["json", "unknown", "number", "rewrite", "duplicate", "too_many"])
async def test_invalid_response_does_not_fall_back_to_candidates(remembered, kind):
    memory, query, _ = remembered

    def choose(payload):
        key = payload["candidates"][0]["id"]
        return {
            "json": "not json",
            "unknown": {"memory_ids": ["unavailable-id"]},
            "number": {"memory_ids": [0]},
            "rewrite": {"memory_ids": [key], "content": "模型改写后的正文"},
            "duplicate": {"memory_ids": [key, key]},
            "too_many": {"memory_ids": [key] * 7},
        }[kind]

    invocation, events = run_gate(memory, query, Picker(choose))
    assert await invocation == ("", [])
    assert events[-1][1]["status"] == "unavailable"
    assert events[-1][1]["selected_count"] == 0


@pytest.mark.parametrize(
    "query,budget", [("外观颜色", 8000), (None, 8000), ("真空", 0), ("真空", 10)]
)
async def test_no_eligible_input_or_budget_makes_no_model_request(remembered, query, budget):
    memory, _, _ = remembered
    model = Picker(lambda _: pytest.fail("没有可带入的候选时不应调用模型"))
    invocation, _ = run_gate(memory, query, model, max_tokens=budget)
    assert await invocation == ("", []) and not model.calls


@pytest.mark.parametrize("change", ["message", "delete", "revision", "source"])
async def test_changes_while_awaiting_model_invalidate_stale_approval(services, remembered, change):
    memory, query, candidates = remembered
    wanted = next(fact for _, fact in candidates["matches"] if fact["title"] == "ZX2200真空V2")

    def choose(_payload):
        if change == "revision":
            bundle = memory.generated.bundle("local", memory.workspace.id)
            bundle["document"]["groups"][0]["title"] += "（更新）"
            memory.generated.publish(
                {"owner_id": "local", "workspace_id": memory.workspace.id}, bundle["document"]
            )
        elif change == "source":
            (memory.workspace.root / "Program.cs").write_text("class Changed {}", encoding="utf-8")
        else:
            with services[1].session.begin() as session:
                if change == "delete":
                    session.get(Thread, wanted["thread_id"]).state = "deleted"
                else:
                    session.get(
                        Message, wanted["evidence"][0]["message_id"]
                    ).content = "原条件已撤回。"
        return {"memory_ids": [wanted["id"]]}

    invocation, _ = run_gate(memory, query, Picker(choose))
    assert await invocation == ("", [])


async def test_large_candidates_are_reviewed_in_complete_bounded_batches(services, monkeypatch):
    memory = services[4]
    monkeypatch.setattr(catalog(services[1]).retrieval, "scores", lambda *_: {})
    for index in range(3):
        seed_memory(memory, MemorySeed(f"真空条件{index}", "真空释放的适用条件。" * 40))
    model = Picker(lambda payload: {"memory_ids": [row["id"] for row in payload["candidates"]]})
    settings = ModelSettings(context_tokens=2048, output_tokens=512)
    invocation, _ = run_gate(memory, "真空条件", model, settings=settings)
    prompt, rows = await invocation
    assert len(model.calls) > 1 and len(rows[0]["memory_ids"]) == 3 and prompt
    for messages, _ in model.calls:
        assert estimate_tokens(messages) <= input_budget(settings.context_tokens, 512)
        payload = json.loads(messages[-1].text)
        assert all(row["content"] == "真空释放的适用条件。" * 40 for row in payload["candidates"])


async def test_failure_in_a_later_batch_discards_earlier_approvals(services, monkeypatch):
    memory = services[4]
    monkeypatch.setattr(catalog(services[1]).retrieval, "scores", lambda *_: {})
    for index in range(3):
        seed_memory(memory, MemorySeed(f"真空条件{index}", "真空释放的适用条件。" * 40))
    model = None

    def choose(payload):
        if len(model.calls) > 1:
            raise RuntimeError("secret-provider-detail")
        return {"memory_ids": [row["id"] for row in payload["candidates"]]}

    model = Picker(choose)
    invocation, events = run_gate(
        memory, "真空条件", model, settings=ModelSettings(context_tokens=2048, output_tokens=512)
    )
    assert await invocation == ("", [])
    assert "secret-provider-detail" not in str(events)


async def test_timeout_discards_memories_and_external_cancellation_propagates(
    remembered, monkeypatch
):
    memory, query, _ = remembered
    entered = asyncio.Event()

    async def blocked(_payload):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("app.modules.memory.selection.SELECTION_TIMEOUT", 0.01)
    invocation, events = run_gate(memory, query, Picker(blocked))
    assert await invocation == ("", []) and events[-1][1]["error_type"] == "TimeoutError"
    monkeypatch.setattr("app.modules.memory.selection.SELECTION_TIMEOUT", 30)
    entered.clear()
    invocation, _ = run_gate(memory, query, Picker(blocked))
    task = asyncio.create_task(invocation)
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_selection_uses_existing_project_budget_callbacks(services, remembered):
    memory, query, candidates = remembered
    wanted = candidates["matches"][0][1]["id"]
    observed = []

    class Provider(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            observed.append(messages)
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content=json.dumps({"memory_ids": [wanted]}),
                            usage_metadata={
                                "input_tokens": 50,
                                "output_tokens": 5,
                                "total_tokens": 55,
                            },
                        )
                    )
                ]
            )

    ledger = ModelLedger(services[1], "memory-selection-budget")
    ledger.save({"token_limit": 20000})
    model = Provider(callbacks=[ProjectModelBudget(ledger, 8192, output_tokens=512)])
    invocation, _ = run_gate(memory, query, model)
    assert (await invocation)[1] and ledger.tokens()["reserved_tokens"] == 55
    ledger.save({"token_limit": 1000})
    ledger.reserve(945)
    assert ledger.tokens()["reserved_tokens"] == 1000
    observed.clear()
    invocation, events = run_gate(memory, query, model)
    assert await invocation == ("", []) and not observed
    assert events[-1][1]["status"] == "unavailable"


async def test_account_change_while_model_waits_does_not_inject_prior_account_memory(remembered):
    memory, query, _ = remembered
    token = None

    def choose(payload):
        nonlocal token
        token = request_identity.set({"user": {"id": "other-account", "role": "user"}})
        return {"memory_ids": [payload["candidates"][0]["id"]]}

    try:
        invocation, _ = run_gate(memory, query, Picker(choose))
        assert await invocation == ("", [])
    finally:
        if token is not None:
            request_identity.reset(token)


async def test_runtime_answer_only_receives_approved_memory_not_other_candidates(
    services, remembered, monkeypatch
):
    memory, query, _ = remembered
    answer_context, selector_context = [], []

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            if "你只负责复核长期记忆" in messages[0].text:
                payload = json.loads(messages[-1].text)
                selector_context.extend(row["content"] for row in payload["candidates"])
                wanted = next(
                    row["id"] for row in payload["candidates"] if row["title"] == "ZX2200真空V2"
                )
                return ChatResult(
                    generations=[
                        ChatGeneration(
                            message=AIMessage(content=json.dumps({"memory_ids": [wanted]}))
                        )
                    ]
                )
            answer_context.extend(message.text for message in messages)
            return super()._generate(messages, *args, **kwargs)

    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_args, **_kwargs: Model()
    )
    runtime = AgentRuntime(services[0], services[5], services[2], services[3], memory)
    run = services[3].create_run(None, query, [])
    await runtime.execute(run, lambda kind, row: services[3].event(run["id"], kind, row))
    assert len(selector_context) == 2 and any("另一套参数" in row for row in selector_context)
    assert "必须确认负压已经释放" in "\n".join(answer_context)
    assert "另一套参数" not in "\n".join(answer_context)
    rows = services[3].latest_event(run["thread_id"], "context_sources")["memories"]
    assert "另一套参数" not in str(rows) and len(rows[0]["memory_ids"]) == 1


async def test_readonly_state_inspection_does_not_invoke_selection_model(
    services, remembered, monkeypatch
):
    memory, query, _ = remembered
    captured = {}

    def capture(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_deep_agent", capture)
    runtime = AgentRuntime(services[0], services[5], services[2], services[3], memory)
    await runtime.graph(
        "inspection-test", None, lambda *_: None, inspection=True, memory_query=query
    )
    assert "必须确认负压已经释放" not in captured["system_prompt"]


async def test_rejected_or_failed_memory_selection_does_not_stop_normal_answer(
    services, remembered, monkeypatch
):
    memory, query, _ = remembered
    observed = []

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            if "你只负责复核长期记忆" in messages[0].text:
                return ChatResult(
                    generations=[ChatGeneration(message=AIMessage(content="invalid"))]
                )
            observed.extend(message.text for message in messages)
            return super()._generate(messages, *args, **kwargs)

    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_args, **_kwargs: Model()
    )
    runtime = AgentRuntime(services[0], services[5], services[2], services[3], memory)
    run = services[3].create_run(None, query, [], source_options={"use_memory": True})
    answer = await runtime.execute(run, lambda kind, row: services[3].event(run["id"], kind, row))
    assert answer == "测试回复" and "必须确认负压已经释放" not in "\n".join(observed)
    assert services[3].latest_event(run["thread_id"], "context_sources")["memories"] == []
