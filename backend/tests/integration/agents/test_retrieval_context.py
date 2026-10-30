"""追问的背景边界、真实召回与筛选、旧用户消息的请求级裁剪。"""

import json

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.context.history_plan import HistoryPlan
from app.agents.context.retrieval_context import retrieval_context
from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from app.modules.memory.selection import MemorySelection
from tests.helpers.memories import MemorySeed, seed_memory
from tests.helpers.models import DeterministicModel


def test_context_is_bounded_preserves_latest_correction_and_does_not_copy_selections():
    messages = [{"role": "user", "content": f"old-{n}-" + "x" * 2000} for n in range(20)]
    messages[-1] = {"role": "user", "content": "纠正：本轮改问设备B V3。"}
    context = retrieval_context(messages, [{"path": "A.cs", "content": "不得复制整个选区"}])
    assert len(context["recent"]) <= 12
    assert sum(len(row["content"]) for row in context["recent"]) <= 6000
    assert context["recent"][-1]["content"] == messages[-1]["content"]
    assert "old-0-" not in str(context) and "不得复制整个选区" not in str(context)
    assert context["selection_paths"] == ["A.cs"]
    assert any(row["partial"] for row in context["recent"])


def test_old_user_constraints_can_stay_without_irrelevant_answer_or_unrelated_old_question():
    messages = [
        HumanMessage(content="全程只读，禁止改动设备。"),
        AIMessage(content="无关旧事实777。"),
        HumanMessage(content="介绍Vue。"),
        AIMessage(content="旧框架解释888。"),
    ]
    messages += [
        row
        for n in range(6)
        for row in (HumanMessage(content=f"近期{n}"), AIMessage(content=f"回复{n}"))
    ]
    plan = HistoryPlan(messages)
    constraint = next(
        row for row in plan.candidates if row["kind"] == "user" and "只读" in row["content"]
    )
    projected = "\n".join(row.text for row in plan.render({constraint["id"]}))
    assert "全程只读" in projected and "近期5" in projected
    assert all(text not in projected for text in ("777", "888", "介绍Vue"))
    assert len(messages) == 16 and messages[2].text == "介绍Vue。"
    reply = next(row for row in plan.candidates if "888" in str(row))
    restored = plan.render({reply["id"]})
    assert restored[:2] == messages[2:4]  # 被选中的旧回复必须带回其原问题。


async def test_memory_recall_and_filter_share_followup_background(services, monkeypatch):
    from app.modules.knowledge.search import catalog

    memory = services[4]
    monkeypatch.setattr(catalog(services[1]).retrieval, "scores", lambda *_: {})
    seed_memory(memory, MemorySeed("ZX2200真空V2", "ZX2200 V2真空标定前必须释放负压。"))
    context = retrieval_context(
        [
            {"role": "user", "content": "现在讨论ZX2200 V2真空标定。"},
            *[{"role": "user", "content": "继续核对。"} for _ in range(5)],
        ]
    )
    requests = []

    class Picker:
        async def ainvoke(self, messages, **kwargs):
            payload = json.loads(messages[-1].text)
            requests.append(payload)
            return AIMessage(
                content=json.dumps({"memory_ids": [row["id"] for row in payload["candidates"]]})
            )

    assert not memory.candidates("它有哪些前提？")["matches"]
    gate = MemorySelection(memory, Picker(), ModelSettings(), lambda *_: None)
    prompt, rows = await gate.prepare("它有哪些前提？", context=context)
    assert "释放负压" in prompt and rows
    assert requests[0]["question"] == "它有哪些前提？" and requests[0]["context"] == context


async def test_actual_runtime_uses_only_current_branch_before_question_for_both_filters(
    services, monkeypatch
):
    paths, _, workspace, repository, memory, settings = services
    settings.save(
        AppSettings(
            model=ModelSettings(context_tokens=32768, output_tokens=512),
            mcp_servers=[],
            auto_memory=False,
        )
    )
    thread = repository.create_thread("追问背景")
    first = repository.create_run(thread["id"], "设备A V1真空报警", [])
    repository.finish(first["id"], "需继续核对设备A V1。")
    run = repository.create_run(thread["id"], "它当时怎么解决的？", [])
    contexts = []
    original = memory.candidates

    def candidates(query):
        contexts.append(query)
        return original(query)

    monkeypatch.setattr(memory, "candidates", candidates)
    built = []
    from app.agents.runtime.graph_builder import AgentGraphBuilder

    original_build = AgentGraphBuilder.build

    async def build(self, *args, **kwargs):
        built.append(kwargs.get("retrieval_context"))
        return await original_build(self, *args, **kwargs)

    monkeypatch.setattr(AgentGraphBuilder, "build", build)

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="结合上文核对。"))]
            )

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memory)
    try:
        answer = await runtime.execute(run, lambda *_: None)
        repository.finish(run["id"], answer)
        assert "设备A V1" in contexts[0]
        assert built[0]["recent"][-1]["content"] == "需继续核对设备A V1。"
        assert "它当时怎么解决的" not in str(built[0])
        later = repository.create_run(thread["id"], "改问未来设备B V9，不能进入旧问题重答。", [])
        repository.finish(later["id"], "未来消息LATER_NOISE_999")
        regenerated = repository.regenerate(run["id"])
        await runtime.execute(regenerated, lambda *_: None)
        assert "设备A V1" in str(built[-1])
        assert "未来设备B" not in str(built[-1]) and "LATER_NOISE_999" not in str(built[-1])
    finally:
        runtime.semantic.close()
