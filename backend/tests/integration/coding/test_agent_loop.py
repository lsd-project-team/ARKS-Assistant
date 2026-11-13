"""聊天工具链在空项目里创建文件并执行命令的端到端回归。"""

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.agents.runtime.engine import AgentRuntime
from app.core.config import Paths
from app.modules.chat.schemas import SourceOptions
from app.modules.source_analysis.workspace import Workspace
from tests.helpers.models import DeterministicModel


class CodingAgentModel(DeterministicModel):
    calls: list[str] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tools = [message for message in messages if isinstance(message, ToolMessage)]
        last = tools[-1] if tools else None
        if last is None:
            name, args = "write_file", {"path": "hello.txt", "content": "hello 通信"}
        elif last.name == "write_file":
            name, args = "run_command", {"command": "dotnet --version"}
        else:
            return ChatResult(
                generations=[
                    ChatGeneration(message=AIMessage(content="已创建文件并检查构建环境。"))
                ]
            )
        self.calls.append(name)
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[{"id": f"call-{len(tools)}", "name": name, "args": args}],
                    )
                )
            ]
        )


@pytest.mark.asyncio
async def test_agent_creates_file_and_runs_command_in_project(services, tmp_path, monkeypatch):
    paths, _, _, repository, memories, settings = services
    root = tmp_path / "project"
    root.mkdir()
    runtime = AgentRuntime(Paths(paths.data, root), settings, Workspace(root), repository, memories)
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *args, **kwargs: model
    )
    model = CodingAgentModel()
    thread = repository.create_thread("编码")["id"]
    run = repository.create_run(
        thread,
        "在这个空项目里创建 hello 文件，并检查构建环境",
        [],
        SourceOptions(use_memory=False, use_knowledge=False).model_dump(),
    )

    events = []
    answer = await runtime.execute(run, lambda kind, payload: events.append((kind, payload)))

    assert "已创建文件" in answer
    assert (root / "hello.txt").read_text(encoding="utf-8") == "hello 通信"
    assert model.calls == ["write_file", "run_command"]
    checkpoints = runtime.coding.checkpoints()
    assert checkpoints["checkpoints"]
    assert any(kind == "coding" for kind, _ in events)
    changes = [payload for kind, payload in events if kind == "coding_changes"]
    assert changes and changes[0]["files"][0]["path"] == "hello.txt"
    assert changes[0]["files"][0]["status"] == "added"
    assert "+hello" in changes[0]["diff"]
    assert "+hello" in changes[0]["files"][0]["patch"]
    runtime.coding.executor.stop_all()
