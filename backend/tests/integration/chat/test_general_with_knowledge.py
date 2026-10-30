"""普通对话的真实 Agent/仓储/事件组合回归，无关候选不能成为拒答原因。"""

import asyncio

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings
from app.modules.chat.context import ConversationContext
from app.modules.chat.runs import RunManager
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus
from app.modules.knowledge.semantic import SemanticRetrieval
from tests.helpers.models import DeterministicModel


@pytest.mark.parametrize(
    "question,original",
    [
        ("你好", "你好！有什么可以帮你？"),
        ("给我介绍一下vue框架", "Vue 是用于构建用户界面的框架。"),
        ("解释HTTP和WebSocket的区别", "HTTP 常用于请求与响应，WebSocket 支持双向持续通信。"),
        ("翻译成英文：早上好", "Good morning."),
    ],
)
@pytest.mark.parametrize("with_history", [False, True])
@pytest.mark.parametrize("use_knowledge", [False, True])
async def test_general_reply_never_loads_or_searches_knowledge_before_answering(
    services, monkeypatch, question, original, with_history, use_knowledge
):
    paths, database, workspace, repository, memories, settings = services
    settings.save(AppSettings(mcp_servers=[], auto_memory=False))
    DebugIssues(HandoverStore(database=database)).save(
        DebugWrite(title="真空报警处理记录", payload={"problem": "报警后检查气路，试验值为42。"}),
        {},
    )

    def forbidden(*_args, **_kwargs):
        pytest.fail("普通问题在决定调用工具前不能加载问题库或执行检索")

    monkeypatch.setattr(DebugIssueCorpus, "__init__", forbidden)
    phases = []

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            assert "你只负责筛选资料" not in messages[0].text
            assert "你负责核查历史经验回答" not in messages[0].text
            assert "真空报警处理记录" not in messages[0].text
            assert ("问题识别与查询路由" in messages[0].text) is use_knowledge
            phases.append("answer")
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=original))])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    manager = RunManager(repository, runtime, settings)
    options = {"use_memory": False, "use_knowledge": use_knowledge, "use_deepwiki": False}
    thread_id = None
    if with_history:
        prior = repository.create_run(None, "查一下真空报警记录", [], options)
        repository.finish(prior["id"], "前文曾查过真空报警处理记录。")
        thread_id = prior["thread_id"]
    run = repository.create_run(thread_id, question, [], options)
    try:
        manager.start(run)
        await asyncio.gather(*manager.tasks.values())
        assert repository.run(run["id"])["status"] == "completed"
        assert repository.thread(run["thread_id"])["messages"][-1]["content"] == original
        events = repository.events(run["id"])
        assert repository.run_event(run["id"], "context_sources")["debug_issues"] == []
        assert not {
            "knowledge_search",
            "knowledge_selection",
            "knowledge_answer_review",
            "tool_start",
        } & {row["kind"] for row in events}
        assert phases == ["answer"]
        usage = [row for row in events if row["kind"] == "provider_usage"]
        assert len(usage) == 1 and usage[0]["payload"]["purpose"] == "answer"
        assert "没有选到" not in str([row["payload"] for row in events])
    finally:
        await manager.shutdown()
        runtime.semantic.close()


async def test_followup_reusing_record_reference_is_loaded_and_fact_checked_without_search(
    services, monkeypatch
):
    paths, database, workspace, repository, memories, settings = services
    settings.save(AppSettings(mcp_servers=[], auto_memory=False))
    saved = DebugIssues(HandoverStore(database=database)).save(
        DebugWrite(title="已读试验", payload={"problem": "本次结果为42。"}), {}
    )
    reference = f"[已读试验](debug-issue:{saved['id']}/1)"

    def forbidden(*_args, **_kwargs):
        pytest.fail("复用已有编号引用时不应执行相似度检索")

    monkeypatch.setattr(SemanticRetrieval, "scores", forbidden)

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            if (
                "你只负责筛选资料" in messages[0].text
                or "你负责核查历史经验回答" in messages[0].text
            ):
                return super()._generate(messages, *args, **kwargs)
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="本次42。" + reference))]
            )

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    options = {"use_memory": False, "use_knowledge": True, "use_deepwiki": False}
    prior = repository.create_run(None, "查询试验结果", [], options)
    repository.finish(prior["id"], "本次结果为42。" + reference)
    run = repository.create_run(prior["thread_id"], "那这次结果是多少", [], options)
    try:
        answer = await runtime.execute(
            run, lambda kind, row: repository.event(run["id"], kind, row)
        )
        assert "42" in answer and reference in answer
        assert repository.run_event(run["id"], "knowledge_answer_review")["verdict"] == "passed"
        assert repository.run_event(run["id"], "knowledge_search") is None
        context = ConversationContext(runtime).run_sources(run["id"])
        assert [row["id"] for row in context["debug_issues"]] == [saved["id"]]
    finally:
        runtime.semantic.close()
