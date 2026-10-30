"""真实文件/API/Agent 请求验证，模型网络使用确定性替身。"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain.agents.middleware.types import ModelRequest
from langchain_core.exceptions import ContextOverflowError
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.context.budget import ContextBudget
from app.agents.context.instructions import (
    GlobalAgentInstructions,
    bind_agent_instructions,
    instruction_snapshot,
)
from app.agents.context.tokens import current_budget, estimate_tokens, request_budget
from app.agents.runtime.engine import AgentRuntime
from app.bootstrap import create_app
from app.core.config import AppSettings, Paths
from app.infrastructure.storage.backup import create_backup
from app.infrastructure.storage.restore import restore_backup
from app.modules.auth.context import request_identity
from app.modules.chat.context import ConversationContext
from app.modules.chat.runs import RunManager
from app.modules.settings.agent_instructions import (
    EMPTY_VERSION,
    MAX_INSTRUCTION_BYTES,
    AgentInstructionsStore,
)
from tests.helpers.accounts import sign_in
from tests.helpers.models import DeterministicModel


def test_utf8_file_empty_clear_reload_and_optimistic_version(tmp_path):
    store = AgentInstructionsStore(tmp_path)
    assert store.read("first")["content"] == "" and not store.root.exists()
    content = "# 回答习惯\r\n默认用中文🙂。\r\n"
    saved = store.save("first", content, EMPTY_VERSION)
    assert store.path("first").read_bytes() == content.encode("utf-8")
    assert AgentInstructionsStore(tmp_path).read("first") == saved
    with pytest.raises(ValueError, match="其他窗口"):
        store.save("first", "不能覆盖新版本", EMPTY_VERSION)
    assert store.read("first") == saved
    assert store.read("second")["content"] == ""
    cleared = store.save("first", "", saved["version"])
    assert cleared["content"] == "" and cleared["version"] == EMPTY_VERSION


def test_size_limit_is_utf8_bytes_and_rejects_without_overwriting(tmp_path):
    store = AgentInstructionsStore(tmp_path)
    valid = "中" * (MAX_INSTRUCTION_BYTES // 3)
    saved = store.save("first", valid, EMPTY_VERSION)
    with pytest.raises(ValueError, match="32 KiB"):
        store.save("first", valid + "中", saved["version"])
    assert store.read("first")["content"] == valid
    store.save("second", "a" * MAX_INSTRUCTION_BYTES, EMPTY_VERSION)
    assert store.path("../outside").is_relative_to(store.root)


def test_concurrent_edits_cannot_silently_overwrite_one_another(tmp_path):
    store = AgentInstructionsStore(tmp_path)

    def write(value):
        try:
            return store.save("first", value, EMPTY_VERSION)["content"]
        except ValueError:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(write, ["第一份完整指令", "第二份完整指令"]))
    assert sum(value is not None for value in results) == 1
    assert store.read("first")["content"] in results
    assert not list(store.root.rglob("*.tmp"))


@pytest.mark.authentication
def test_api_is_personal_for_normal_users_and_cannot_be_forged(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        assert client.get("/api/agent-instructions").status_code == 401
        first = sign_in(client, "user").json()["user"]
        before = client.get("/api/agent-instructions").json()
        response = client.put(
            "/api/agent-instructions",
            json={
                "content": "甲的全局偏好",
                "version": before["version"],
            },
        )
        assert response.status_code == 200 and response.json()["owner_id"] == first["id"]
        assert (
            client.put(
                "/api/agent-instructions",
                json={
                    "content": "篡改",
                    "version": before["version"],
                    "owner_id": "other",
                },
            ).status_code
            == 422
        )
        assert (
            client.put(
                "/api/agent-instructions",
                json={
                    "content": "旧窗口",
                    "version": before["version"],
                },
            ).status_code
            == 409
        )
        sign_in(client, "admin")
        assert client.get("/api/agent-instructions").json()["content"] == ""
        assert client.get(f"/api/agent-instructions?owner_id={first['id']}").json()["content"] == ""
        assert client.get("/api/p/independent/agent-instructions").status_code == 404
        sign_in(client, "user")
        assert client.get("/api/agent-instructions").json()["content"] == "甲的全局偏好"


async def test_real_agent_injects_user_role_and_never_persists_as_chat_message(
    services, monkeypatch
):
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    paths, _, workspace, repository, memories, settings = services
    (workspace.root / "AGENTS.md").write_text("项目级指令禁止自动加载标记", encoding="utf-8")
    settings.save(AppSettings(mcp_servers=[]))
    store, seen = AgentInstructionsStore(paths.data), []
    store.save(
        "first", '全局指令独有标记：先给结论。\napi_key="instruction-test-secret"', EMPTY_VERSION
    )

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            seen.append(messages)
            return super()._generate(messages, *args, **kwargs)

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    token = request_identity.set({"user": {"id": "first", "role": "admin"}})
    try:
        run = repository.create_run(
            None,
            "本题明确要求：这次请用英文。",
            [],
            {
                "use_memory": False,
                "use_knowledge": False,
                "use_deepwiki": False,
            },
        )
        answer = await runtime.execute(
            run, lambda kind, row: repository.event(run["id"], kind, row)
        )
        repository.finish(run["id"], answer)
        messages = seen[-1]
        instructions = [row for row in messages if "全局指令独有标记" in row.text]
        assert len(instructions) == 1 and isinstance(instructions[0], HumanMessage)
        assert messages.index(instructions[0]) < next(
            i for i, row in enumerate(messages) if "本题明确要求" in row.text
        )
        assert "全局指令独有标记" not in messages[0].text
        assert all("项目级指令禁止自动加载标记" not in row.text for row in messages)
        assert all("instruction-test-secret" not in row.text for row in messages)
        assert all(
            "全局指令独有标记" not in row["content"]
            for row in repository.thread(run["thread_id"])["messages"]
        )
        async with AsyncSqliteSaver.from_conn_string(
            str(paths.data / "checkpoints.sqlite3")
        ) as saver:
            checkpoints = [
                row.checkpoint
                async for row in saver.alist({"configurable": {"thread_id": run["thread_id"]}})
            ]
            archived = repr(checkpoints)
            assert "本题明确要求" in archived
            assert "全局指令独有标记" not in archived
        context = ConversationContext(runtime).run_sources(run["id"])
        assert context["agent_instructions"]["content"].startswith("全局指令独有标记")
        assert "instruction-test-secret" not in repr(context)
        assert context["budget"]["breakdown"]["instructions"] > 0
    finally:
        request_identity.reset(token)


async def test_run_freezes_instructions_from_submitter_not_dispatcher(services):
    store = AgentInstructionsStore(services[0].data)
    saved = store.save("first", "发起账号旧版偏好", EMPTY_VERSION)
    store.save("second", "另一个账号偏好", EMPTY_VERSION)
    observed = []

    class Runtime:
        async def execute(self, *_):
            observed.append(instruction_snapshot(services[0]))
            return "完成"

    first = request_identity.set({"user": {"id": "first", "role": "admin"}})
    run = services[3].create_run(None, "需要排队处理的问题", [])
    request_identity.reset(first)
    manager = RunManager(services[3], Runtime(), services[5])
    second = request_identity.set({"user": {"id": "second", "role": "admin"}})
    try:
        manager.start(run)
        store.save("first", "刚保存的新偏好", saved["version"])
        await asyncio.gather(*manager.tasks.values())
    finally:
        request_identity.reset(second)
    assert observed[0]["content"] == "发起账号旧版偏好"
    assert observed[0]["owner_id"] == "first"


async def test_instruction_budget_is_preserved_when_checkpoint_excludes_instructions():
    snapshot = {"content": "长期偏好：" + "简洁中文" * 100, "owner_id": "first"}
    middleware = GlobalAgentInstructions(snapshot)
    request = ModelRequest(
        model=DeterministicModel(),
        system_message=SystemMessage(content="系统"),
        messages=[HumanMessage(content="当前问题")],
    )

    async def capture(prepared):
        budget = request_budget(prepared, 8192, 256)
        assert sum(budget["breakdown"].values()) == estimate_tokens(
            [prepared.system_message, *prepared.messages]
        )
        restored = current_budget(request.messages, budget, 8192, 256)
        assert restored["breakdown"]["instructions"] == budget["breakdown"]["instructions"]
        assert restored["tokens"] == budget["tokens"]
        return budget

    await middleware.awrap_model_call(request, capture)


async def test_over_budget_instructions_never_reach_provider():
    middleware = GlobalAgentInstructions({"content": "长指令" * 4000})
    budget = ContextBudget(2048, 256, "", lambda *_: None)
    request = ModelRequest(model=DeterministicModel(), messages=[HumanMessage(content="问题")])

    async def forbidden(_request):
        pytest.fail("超量的指令不能发送供应商")

    with pytest.raises(ContextOverflowError):
        await middleware.awrap_model_call(
            request, lambda prepared: budget.awrap_model_call(prepared, forbidden)
        )


def test_trace_hides_other_accounts_instruction_snapshots(services):
    from app.modules.memory.visibility import visible_run_event

    event = {"kind": "agent_instructions", "payload": {"owner_id": "first", "content": "PRIVATE"}}
    token = request_identity.set({"user": {"id": "second", "role": "admin"}})
    try:
        assert visible_run_event(event, "first") is None
    finally:
        request_identity.reset(token)


def test_backup_roundtrip_and_old_backup_preserves_existing_instructions(services, tmp_path):
    paths = services[0]
    old_backup = create_backup(paths)
    store = AgentInstructionsStore(paths.data)
    store.save("first", "备份中的全局指令", EMPTY_VERSION)
    backup = create_backup(paths)
    target = Paths(tmp_path / "restored", paths.workspace)
    restore_backup(backup, target.data)
    restored = AgentInstructionsStore(target.data)
    assert restored.read("first")["content"] == "备份中的全局指令"
    restore_backup(old_backup, target.data)
    assert restored.read("first")["content"] == "备份中的全局指令"


def test_restore_failure_rolls_back_existing_global_instruction_bytes(
    services, tmp_path, monkeypatch
):
    store = AgentInstructionsStore(services[0].data)
    store.save("first", "备份版本", EMPTY_VERSION)
    backup = create_backup(services[0])
    target = Paths(tmp_path / "target", services[0].workspace)
    current = AgentInstructionsStore(target.data)
    saved = current.save("first", "目标机器原来的指令\r\n", EMPTY_VERSION)
    original, failed = Path.rename, False

    def fail_install(source, destination):
        nonlocal failed
        if (
            not failed
            and source.name == "instructions"
            and Path(destination) == target.data / "instructions"
        ):
            failed = True
            raise OSError("controlled install failure")
        return original(source, destination)

    monkeypatch.setattr(Path, "rename", fail_install)
    with pytest.raises(ValueError, match="旧数据已回滚"):
        restore_backup(backup, target.data)
    assert current.read("first")["content"] == saved["content"]
    assert current.path("first").read_bytes() == saved["content"].encode("utf-8")


def test_unbound_snapshot_uses_current_account_and_empty_file_is_ignored(services):
    from app.agents.context.instructions import instruction_messages

    store = AgentInstructionsStore(services[0].data)
    saved = store.save("first", "甲的默认要求", EMPTY_VERSION)
    token = request_identity.set({"user": {"id": "first", "role": "admin"}})
    try:
        assert instruction_snapshot(services[0])["version"] == saved["version"]
        with bind_agent_instructions(saved):
            assert instruction_snapshot(services[0]) == saved
    finally:
        request_identity.reset(token)
    assert instruction_messages({"content": " \n"}) == []


@pytest.mark.authentication
def test_shared_chat_context_trace_and_events_hide_private_instructions(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        first = sign_in(client, "user").json()["user"]
        project = client.post("/api/projects", json={"name": "个人指令边界"}).json()
        repository = app.state.projects.services(project["id"]).repository
        token = request_identity.set({"user": first})
        try:
            run = repository.create_run(None, "公开问题", [])
        finally:
            request_identity.reset(token)
        repository.event(
            run["id"],
            "agent_instructions",
            {
                "owner_id": first["id"],
                "version": "a" * 64,
                "content": "PRIVATE-INSTRUCTIONS",
            },
        )
        repository.finish(run["id"], "公开回答")
        prefix = f"/api/p/{project['id']}/runs/{run['id']}"
        assert "PRIVATE-INSTRUCTIONS" in client.get(prefix + "/context").text
        sign_in(client, "admin")
        for suffix in ("context", "trace", "events"):
            response = client.get(prefix + "/" + suffix)
            assert response.status_code == 200
            assert "PRIVATE-INSTRUCTIONS" not in response.text
