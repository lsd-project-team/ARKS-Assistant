"""暂停的资料不能进入新问答；其他来源和原始记录仍可使用。"""

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, McpSettings, ModelSettings
from app.modules.chat.context import ConversationContext
from app.modules.chat.schemas import SourceOptions
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.handover_materials import HandoverMaterialCorpus
from app.modules.projects.models import Project
from tests.helpers.memories import MemorySeed as MemoryWrite
from tests.helpers.memories import seed_memory
from tests.helpers.models import DeterministicModel


@pytest.mark.parametrize("use_knowledge", [True, False])
async def test_paused_sources_are_absent_while_other_enabled_sources_work(
    services, monkeypatch, use_knowledge
):
    paths, database, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(
            model=ModelSettings(context_tokens=32768, output_tokens=512),
            deepwiki_repo="test/example",
            mcp_servers=[McpSettings(id="wiki", name="DeepWiki", url="https://example.test/mcp")],
        )
    )
    project_id = "sources-project"
    with database.session.begin() as session:
        session.add(Project(id=project_id, name="来源测试", source_root=str(paths.workspace)))
    repository.project_id = project_id
    store = HandoverStore(database=database)
    handover = store.create(
        "source", "取片不稳定", {"content": "取片不稳定的交接资料暂停标记"}, "测试"
    )
    issue = DebugIssues(store).save(
        DebugWrite(
            title="取片不稳定",
            payload={
                "problem": "取片不稳定",
                "solution": "问题与经验保留标记",
                "resolution_status": "resolved",
            },
        ),
        {},
    )
    seed_memory(
        memories,
        MemoryWrite(
            name="取片偏好.md",
            scope="user",
            content="个人偏好保留标记：讲解取片时保留适用条件，用中文回答",
        ),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    tools, prompts, connections = [], [], []

    class Model(DeterministicModel):
        def bind_tools(self, supplied, **_kwargs):
            tools.extend(item.name for item in supplied)
            return self

        def _generate(self, messages, *args, **kwargs):
            prompts.extend(message.text for message in messages)
            if (
                use_knowledge
                and "问题识别与查询路由" in messages[0].text
                and not any(isinstance(row, ToolMessage) for row in messages)
            ):
                return ChatResult(
                    generations=[
                        ChatGeneration(
                            message=AIMessage(
                                content="",
                                tool_calls=[
                                    {
                                        "id": "lookup",
                                        "name": "search_debug_issues",
                                        "args": {"query": "取片不稳定"},
                                    }
                                ],
                            )
                        )
                    ]
                )
            return super()._generate(messages, *args, **kwargs)

    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_args, **_kwargs: Model()
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("暂不接入的流程说明或交接资料不能进入对话")

    monkeypatch.setattr(runtime.knowledge, "tools", forbidden)
    monkeypatch.setattr(HandoverMaterialCorpus, "__init__", forbidden)

    @tool
    async def deepwiki_probe(query: str) -> str:
        """Deterministic stand-in for a configured remote DeepWiki tool."""
        return query

    async def remote_tools(servers, _emit):
        connections.extend(server.name for server in servers)
        return [deepwiki_probe]

    monkeypatch.setattr(runtime, "remote_tools", remote_tools)
    options = SourceOptions(use_knowledge=use_knowledge).model_dump()
    run = repository.create_run(None, "取片不稳定有哪些处理经验", [], options)
    answer = await runtime.execute(
        run, lambda kind, payload: repository.event(run["id"], kind, payload)
    )
    assert answer == "测试回复"
    assert connections == ["DeepWiki"]
    assert {"read_source", "deepwiki_probe"} <= set(tools)
    assert "remember" not in tools
    assert not {
        "search_project_knowledge",
        "search_handover_materials",
        "read_handover_material",
        "search_project_materials",
        "read_project_material",
        "search_project_reading",
        "project_reading_status",
        "start_project_reading",
    } & set(tools)
    text = "\n".join(prompts)
    assert "个人偏好保留标记" in text
    assert "交接资料暂停标记" not in text
    assert "本轮未接入流程图谱、功能说明和交接资料" in text
    assert not hasattr(runtime, "project_reading")
    assert ("问题与经验保留标记" in text) is use_knowledge
    assert ("search_debug_issues" in tools) is use_knowledge
    snapshot = ConversationContext(runtime).run_sources(run["id"])
    assert snapshot["handover_materials"] == []
    assert snapshot["knowledge_retrieval"] == []
    assert "materials" not in snapshot
    assert [row["id"] for row in snapshot["debug_issues"]] == (
        [issue["id"]] if use_knowledge else []
    )
    assert store.get(handover["id"])["payload"]["content"] == "取片不稳定的交接资料暂停标记"


@pytest.mark.parametrize("with_selection", [False, True])
async def test_code_question_and_selection_do_not_automatically_load_flow_guides(
    services, monkeypatch, with_selection
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(model=ModelSettings(context_tokens=8192, output_tokens=512), mcp_servers=[])
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)

    async def forbidden(*_args, **_kwargs):
        raise AssertionError("代码问题不能再自动补入流程与功能说明")

    monkeypatch.setattr(runtime.knowledge, "prepare", forbidden)

    class ReachedGraph(Exception):
        pass

    async def graph(*_args, **kwargs):
        assert kwargs["source_options"] == SourceOptions().model_dump()
        if with_selection:
            assert "<verified_source_context>" in kwargs["verified_context"]
        raise ReachedGraph

    monkeypatch.setattr(runtime, "graph", graph)
    selections = (
        [
            {
                "path": "Program.cs",
                "start_line": 2,
                "end_line": 2,
                "content": " static void Main() {}",
                "version": workspace.read("Program.cs")["version"],
            }
        ]
        if with_selection
        else []
    )
    run = repository.create_run(None, "请解释 Program.cs 的入口函数", selections)
    with pytest.raises(ReachedGraph):
        await runtime.execute(run, lambda *_args: None)
