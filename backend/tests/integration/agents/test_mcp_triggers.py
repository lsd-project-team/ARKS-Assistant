"""MCP 触发命令：未用命令不接入，用过后本对话保持，新对话重新从命令开始。"""

import pytest

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, McpSettings, ModelSettings
from tests.helpers.models import DeterministicModel

LOCAL = {"use_deepwiki": False, "use_knowledge": False, "use_memory": False}


def triggered_server():
    return McpSettings(
        id="parameter_reuse",
        name="ZX2200 参数复用 MCP",
        transport="stdio",
        command="python",
        trigger="参数复用",
    )


def prepare(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(
            model=ModelSettings(context_tokens=16384, output_tokens=512),
            mcp_servers=[triggered_server()],
        )
    )
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: DeterministicModel()
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    calls = []

    async def remote_tools(servers, _emit):
        calls.append([server.id for server in servers])
        return []

    monkeypatch.setattr(runtime, "remote_tools", remote_tools)
    return runtime, repository, calls


async def test_service_is_not_attached_without_command(services, monkeypatch):
    runtime, repository, calls = prepare(services, monkeypatch)
    run = repository.create_run(None, "点胶针偏移能直接复用吗？", [], LOCAL)
    answer = await runtime.execute(run, lambda *_args: None)
    assert answer == "测试回复"
    assert calls == []


async def test_command_attaches_service_and_follow_ups_keep_it(services, monkeypatch):
    runtime, repository, calls = prepare(services, monkeypatch)
    first = repository.create_run(None, "/参数复用 点胶针偏移能直接复用吗？", [], LOCAL)
    await runtime.execute(first, lambda *_args: None)
    repository.finish(first["id"], "第一答")
    assert calls == [["parameter_reuse"]]
    # 命令只用于选择来源，进入模型的正文不包含命令词。
    assert runtime.input_message(repository.message(first["message_id"])).text == (
        "点胶针偏移能直接复用吗？"
    )
    follow = repository.create_run(first["thread_id"], "那 Dispenser.EditState 呢？", [], LOCAL)
    await runtime.execute(follow, lambda *_args: None)
    repository.finish(follow["id"], "第二答")
    assert calls[-1] == ["parameter_reuse"]
    # 新对话没有命令时回到默认：不接入该服务，本轮不会建立 MCP 连接。
    other = repository.create_run(None, "点胶针偏移能直接复用吗？", [], LOCAL)
    await runtime.execute(other, lambda *_args: None)
    repository.finish(other["id"], "第三答")
    assert len(calls) == 2


async def test_bare_command_is_rejected_without_calling_model(services, monkeypatch):
    runtime, repository, calls = prepare(services, monkeypatch)
    run = repository.create_run(None, "/参数复用", [], LOCAL)
    with pytest.raises(ValueError, match="/参数复用"):
        await runtime.execute(run, lambda *_args: None)
    assert calls == []


def test_commands_endpoint_lists_only_enabled_triggered_servers(services):
    from fastapi.testclient import TestClient

    from app.main import create_app

    paths, _, _, _, _, settings = services
    settings.save(
        AppSettings(
            model=ModelSettings(context_tokens=16384, output_tokens=512),
            mcp_servers=[
                triggered_server(),
                McpSettings(
                    id="disabled",
                    name="已停用",
                    enabled=False,
                    transport="stdio",
                    command="python",
                    trigger="停用服务",
                ),
                McpSettings(
                    id="automatic", name="自动选择", transport="stdio", command="python"
                ),
            ],
        )
    )
    with TestClient(create_app(paths)) as client:
        assert client.get("/api/mcp/commands").json() == {
            "commands": [{"command": "参数复用", "name": "ZX2200 参数复用 MCP"}]
        }
