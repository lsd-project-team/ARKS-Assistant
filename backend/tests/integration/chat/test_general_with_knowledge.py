"""普通对话的真实 Agent/仓储/事件组合回归，无关候选不能成为拒答原因。"""

import asyncio
import json

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings
from app.modules.chat.runs import RunManager
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.semantic import SemanticRetrieval
from tests.helpers.models import DeterministicModel


@pytest.mark.parametrize(
    "question,original",
    [("你好", "你好！有什么可以帮你？"), ("给我介绍一下vue框架", "Vue 是用于构建用户界面的框架。")],
)
async def test_general_reply_survives_unrelated_candidate_persistence_and_replay(
    services, monkeypatch, question, original
):
    paths, database, workspace, repository, memories, settings = services
    settings.save(AppSettings(mcp_servers=[], auto_memory=False))
    DebugIssues(HandoverStore(database=database)).save(
        DebugWrite(title="真空报警处理记录", payload={"problem": "报警后检查气路，试验值为42。"}),
        {},
    )
    # 人为给无关资料高相似度，确保真实检索确实带入，不能靠恰好零命中通过。
    monkeypatch.setattr(
        SemanticRetrieval, "scores", lambda _self, _query, documents: dict.fromkeys(documents, 0.9)
    )
    phases = []

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            if "你只负责筛选资料" in messages[0].text:
                phases.append("selection")
                payload = json.loads(messages[-1].text)
                assert payload["question"] == question and payload["records"]
                assert "answer" not in payload
                content = '{"scope":"general","selections":[]}'
            elif "你负责核查历史经验回答" in messages[0].text:
                pytest.fail("无经验引用的通用回答不应进入历史事实核查")
            else:
                phases.append("answer")
                assert "真空报警处理记录" in messages[0].text
                content = original
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    manager = RunManager(repository, runtime, settings)
    run = repository.create_run(
        None, question, [], {"use_memory": False, "use_knowledge": True, "use_deepwiki": False}
    )
    try:
        manager.start(run)
        await asyncio.gather(*manager.tasks.values())
        assert repository.run(run["id"])["status"] == "completed"
        assert repository.thread(run["thread_id"])["messages"][-1]["content"] == original
        events = repository.events(run["id"])
        assert repository.run_event(run["id"], "context_sources")["debug_issues"]
        assert repository.run_event(run["id"], "knowledge_selection")["scope"] == "general"
        assert repository.run_event(run["id"], "knowledge_answer_review")["verdict"] == "skipped"
        assert [phase for phase in phases] == ["answer", "selection"]
        displayed = [row["payload"]["text"] for row in events if row["kind"] == "answer_replace"]
        assert displayed[-1] == original
        assert "没有选到" not in str([row["payload"] for row in events])
    finally:
        await manager.shutdown()
        runtime.semantic.close()
