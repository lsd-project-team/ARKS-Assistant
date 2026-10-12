import asyncio

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy import func, select

from app.config import AppSettings, McpSettings, ModelSettings
from app.main import create_app
from app.models import QueuedQuestion
from app.repository import Repository
from app.run_feedback import error_feedback
from app.runs import RunManager
from app.runtime import AgentRuntime
from tests.test_compaction import DeterministicModel


@pytest.mark.parametrize("compressed", [False, True])
async def test_edit_rebuilds_context_and_keeps_original_archive(services, monkeypatch, compressed):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings()))
    calls = []

    def generate(_self, messages, *_args, **_kwargs):
        calls.append(messages)
        content = f"验收回答{len(calls)}"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    monkeypatch.setattr(DeterministicModel, "_generate", generate)
    monkeypatch.setattr("app.runtime.create_model", lambda *_a, **_kw: DeterministicModel())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("编辑验收")
    first = repository.create_run(thread["id"], "此前稳定的问题", [])
    repository.finish(first["id"], await runtime.execute(first, lambda *_: None))
    old = repository.create_run(thread["id"], "需要替换的旧问题", [])
    repository.finish(old["id"], await runtime.execute(old, lambda *_: None))
    if compressed:
        async with AsyncSqliteSaver.from_conn_string(
            str(paths.data / "checkpoints.sqlite3")
        ) as saver:
            graph = await runtime.graph(thread["id"], saver, lambda *_: None, inspection=True)
            await graph.aupdate_state(
                {"configurable": {"thread_id": thread["id"]}},
                {
                    "_summarization_event": {
                        "summary_message": HumanMessage(
                            content="旧摘要：需要替换的旧问题 验收回答2"
                        ),
                        "cutoff_index": 2,
                    }
                },
                as_node="model",
            )
    edited = repository.branches.edit_latest(thread["id"], old["message_id"], "修改后的问题", [])
    assert edited["reset_context"]
    repository.finish(edited["id"], await runtime.execute(edited, lambda *_: None))
    prompt = "\n".join(message.text for message in calls[-1])
    assert "此前稳定的问题" in prompt and "验收回答1" in prompt
    assert "修改后的问题" in prompt
    assert "需要替换的旧问题" not in prompt and "验收回答2" not in prompt and "旧摘要" not in prompt
    archive = repository.thread(thread["id"])
    assert len(archive["messages"]) == 6
    assert [row["content"] for row in archive["messages"] if not row["context_active"]] == [
        "需要替换的旧问题",
        "验收回答2",
    ]
    assert archive["editable_message_id"] == edited["message_id"]
    with pytest.raises(ValueError, match="最近"):
        repository.branches.edit_latest(thread["id"], old["message_id"], "过期窗口提交", [])


async def test_fork_uses_chosen_version_and_only_history_before_cursor(services, monkeypatch):
    paths, database, workspace, repository, memories, settings = services
    calls = []

    def generate(_self, messages, *_args, **_kwargs):
        calls.append(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="分支新答案"))])

    monkeypatch.setattr(DeterministicModel, "_generate", generate)
    monkeypatch.setattr("app.runtime.create_model", lambda *_a, **_kw: DeterministicModel())
    thread = repository.create_thread("父会话")
    selection = {
        "path": "Program.cs",
        "content": "分支选区",
        "version": "a" * 64,
        "start_line": 1,
        "end_line": 2,
    }
    original = repository.create_run(thread["id"], "原问题", [selection])
    repository.finish(original["id"], "原回答")
    response_id = repository.run(original["id"])["response_message_id"]
    version = repository.regenerate(original["id"])
    repository.finish(version["id"], "重新生成的回答")
    edited = repository.branches.edit_latest(thread["id"], original["message_id"], "编辑后问题", [])
    repository.finish(edited["id"], "编辑后回答")
    branch = repository.branches.fork(thread["id"], response_id)
    archive = repository.thread(branch["id"])
    assert [row["content"] for row in archive["messages"]] == ["原问题", "原回答"]
    assert archive["messages"][0]["selections"] == [selection]
    assert all(row["context_active"] for row in archive["messages"])
    assert branch["origin_message_id"] == response_id and branch["origin_thread_id"] == thread["id"]
    assert archive["messages"][0]["id"] != original["message_id"]
    run = repository.create_run(branch["id"], "沿这个版本继续", [])
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    repository.finish(run["id"], await runtime.execute(run, lambda *_: None))
    prompt = "\n".join(message.text for message in calls[-1])
    assert all(value in prompt for value in ("原问题", "原回答", "分支选区", "沿这个版本继续"))
    assert "重新生成的回答" not in prompt and "编辑后问题" not in prompt
    assert len(repository.thread(thread["id"])["messages"]) == 5
    with pytest.raises(FileNotFoundError):
        Repository(database, "different-workspace").branches.fork(thread["id"], response_id)
    with pytest.raises(FileNotFoundError):
        repository.branches.fork(thread["id"], run["message_id"])


@pytest.mark.parametrize("before_graph", [False, True])
async def test_interrupted_edit_resumes_once_without_old_context(
    services, monkeypatch, before_graph
):
    paths, _, workspace, repository, memories, settings = services
    fail = False
    calls = []

    def generate(_self, messages, *_a, **_kw):
        if fail and not before_graph:
            raise ConnectionError("编辑回复中断")
        calls.append(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="确定的回复"))])

    def model(*_a, **_kw):
        if fail and before_graph:
            raise ConnectionError("图创建前中断")
        return DeterministicModel()

    monkeypatch.setattr(DeterministicModel, "_generate", generate)
    monkeypatch.setattr("app.runtime.create_model", model)
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("恢复编辑")
    original = repository.create_run(thread["id"], "应移出的旧问题", [])
    repository.finish(original["id"], await runtime.execute(original, lambda *_: None))
    edited = repository.branches.edit_latest(
        thread["id"], original["message_id"], "唯一的新问题", []
    )
    fail = True
    with pytest.raises(ConnectionError):
        await runtime.execute(edited, lambda *_: None)
    repository.set_status(edited["id"], "failed", "验收中断")
    resumed = repository.resume(edited["id"])
    assert resumed["reset_context"]
    fail = False
    repository.finish(resumed["id"], await runtime.execute(resumed, lambda *_: None))
    prompt = "\n".join(message.text for message in calls[-1])
    assert "应移出的旧问题" not in prompt and prompt.count("唯一的新问题") == 1
    assert len(repository.thread(thread["id"])["messages"]) == 4


def test_queue_is_atomic_ordered_versioned_and_survives_repository_reload(services):
    _, database, workspace, repository, _, _ = services
    thread = repository.create_thread("队列验收")
    running = repository.create_run(thread["id"], "当前问题", [])
    first = repository.queue.add(thread["id"], "待发问题一", [])
    second = repository.queue.add(thread["id"], "待发问题二", [])
    assert repository.queue.dispatch(thread["id"]) is None
    updated = repository.queue.update(first["id"], "已修改的问题一", [], first["updated_at"])
    with pytest.raises(ValueError, match="其他窗口"):
        repository.queue.update(first["id"], "过期的修改", [], first["updated_at"])
    repository.finish(running["id"], "当前回答")
    reloaded = Repository(database, workspace.id)
    dispatched = reloaded.queue.dispatch(thread["id"])
    assert repository.message(dispatched["message_id"])["content"] == updated["content"]
    assert [item["id"] for item in reloaded.queue.list(thread["id"])["items"]] == [second["id"]]
    assert reloaded.queue.dispatch(thread["id"]) is None
    with pytest.raises(ValueError, match="开始发送"):
        reloaded.queue.cancel(first["id"])
    reloaded.queue.pause(thread["id"])
    repository.finish(dispatched["id"], "第一问回答")
    assert reloaded.queue.dispatch(thread["id"]) is None
    reloaded.queue.cancel(second["id"])
    assert not reloaded.queue.list(thread["id"])["items"]
    repository.catalog.change(thread["id"], "archived")
    assert reloaded.queue.list(thread["id"])["paused"]
    reloaded.queue.add(thread["id"], "归档后继续提问", [])
    assert repository.catalog.get(thread["id"])["state"] == "active"
    assert reloaded.queue.dispatch(thread["id"]) is None
    reloaded.queue.cancel(reloaded.queue.list(thread["id"])["items"][0]["id"])
    for index in range(20):
        reloaded.queue.add(thread["id"], f"排队{index}", [])
    with pytest.raises(ValueError, match="20"):
        reloaded.queue.add(thread["id"], "超出上限", [])
    repository.catalog.change(thread["id"], "deleted")
    repository.catalog.purge(thread["id"])
    with database.session() as session:
        assert session.scalar(select(func.count()).select_from(QueuedQuestion)) == 0


@pytest.mark.parametrize("outcome", ["completed", "failed", "cancelled"])
async def test_manager_dispatches_on_success_and_pauses_on_stop_or_error(services, outcome):
    _, _, _, repository, _, settings = services
    gate = asyncio.Event()
    entered = asyncio.Event()
    questions = []

    class ControlledRuntime:
        async def execute(self, run, emit):
            question = repository.message(run["message_id"])["content"]
            questions.append(question)
            emit("stage", {"stage": "generating"})
            emit("token", {"text": "已生成部分"})
            if question == "正在运行":
                entered.set()
                await gate.wait()
                if outcome == "failed":
                    raise TimeoutError("等待模型超时")
            return f"回复{question}"

    manager = RunManager(repository, ControlledRuntime(), settings)
    thread = repository.create_thread("队列调度")
    run = repository.create_run(thread["id"], "正在运行", [])
    manager.start(run)
    await asyncio.wait_for(entered.wait(), 2)
    repository.queue.add(thread["id"], "第二个问题", [])
    repository.queue.add(thread["id"], "第三个问题", [])
    first_task = manager.tasks[run["id"]]
    if outcome == "cancelled":
        await manager.cancel(run["id"])
    else:
        gate.set()
        await asyncio.wait_for(first_task, 2)
    while manager.tasks:
        await asyncio.wait_for(asyncio.gather(*list(manager.tasks.values())), 2)
    persisted = repository.run(run["id"])
    assert persisted["status"] == outcome and persisted["started_at"] and persisted["finished_at"]
    assert persisted["stage"] == outcome
    events = repository.events(run["id"], 0)
    assert [event["payload"]["stage"] for event in events if event["kind"] == "stage"] == [
        "queued",
        "generating",
    ]
    queue = repository.queue.list(thread["id"])
    if outcome == "completed":
        assert questions == ["正在运行", "第二个问题", "第三个问题"] and not queue["items"]
    else:
        assert questions == ["正在运行"] and queue["paused"] and len(queue["items"]) == 2
        assert persisted["answer"] == "已生成部分"
        if outcome == "failed":
            assert persisted["error_code"] == "timeout"
        repository.queue.pause(thread["id"], False)
        manager.start(repository.queue.dispatch(thread["id"]))
        while manager.tasks:
            await asyncio.wait_for(asyncio.gather(*list(manager.tasks.values())), 2)
        assert questions == ["正在运行", "第二个问题", "第三个问题"]


def test_recovery_pauses_durable_queue_and_revalidates_waiting_selection(services):
    paths, _, workspace, repository, memories, settings = services
    thread = repository.create_thread("恢复队列")
    run = repository.create_run(thread["id"], "中断的运行", [])
    selection = {
        "path": "Program.cs",
        "start_line": 1,
        "end_line": 2,
        "content": "旧源码",
        "version": workspace.read("Program.cs")["version"],
        "stale": False,
    }
    item = repository.queue.add(thread["id"], "等待的提问", [selection])
    repository.recover()
    assert repository.run(run["id"])["status"] == "interrupted"
    assert (
        repository.queue.list(thread["id"])["paused"]
        and repository.queue.dispatch(thread["id"]) is None
    )
    (workspace.root / "Program.cs").write_text("源码已经变化", encoding="utf-8")
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    message = runtime.current_input(
        {"id": item["id"], "content": item["content"], "selections": [selection]}
    )
    assert "stale=true" in message.text and "历史快照" in message.text
    assert not selection["stale"], "不能改变保存的原始快照"


def test_restart_pauses_queue_after_completed_run_before_dispatch(services):
    repository = services[3]
    thread = repository.create_thread("恰好在出队前退出")
    run = repository.create_run(thread["id"], "已经完成的问题", [])
    item = repository.queue.add(thread["id"], "还没有出队的问题", [])
    repository.finish(run["id"], "已完成回复")
    assert not repository.queue.list(thread["id"])["paused"]
    repository.recover()
    queue = repository.queue.list(thread["id"])
    assert queue["paused"] and queue["items"][0]["id"] == item["id"]
    assert repository.run(run["id"])["status"] == "completed"


def test_workflow_routes_validate_and_keep_failed_edit_input(services, monkeypatch):
    async def waiting(*_args):
        await asyncio.Event().wait()

    monkeypatch.setattr("app.runtime.AgentRuntime.execute", waiting)
    with TestClient(create_app(services[0])) as client:
        run = client.post("/api/threads/start", json={"content": "初始问题"}).json()
        base = f"/api/threads/{run['thread_id']}"
        assert (
            client.post(
                f"{base}/messages/{run['message_id']}/edit", json={"content": "修改"}
            ).status_code
            == 409
        )
        queued = client.post(f"{base}/queue", json={"content": "等待问题"}).json()
        assert queued["started_run"] is None
        item = queued["item"]
        assert (
            client.patch(
                f"/api/queue/{item['id']}",
                json={"content": "已修改等待问题", "version": item["updated_at"]},
            ).status_code
            == 200
        )
        assert (
            client.patch(
                f"/api/queue/{item['id']}",
                json={"content": "旧版本", "version": item["updated_at"]},
            ).status_code
            == 409
        )
        assert client.post(f"{base}/queue", json={"content": "  "}).status_code == 422
        assert client.post(f"/api/runs/{run['id']}/cancel").status_code == 200
        assert client.get(f"{base}/queue").json()["paused"]
        assert (
            client.post(f"{base}/fork", json={"message_id": run["message_id"]}).status_code == 201
        )
        edited = client.post(
            f"{base}/messages/{run['message_id']}/edit", json={"content": "新版本问题"}
        )
        assert edited.status_code == 201 and edited.json()["reset_context"]
        assert client.delete(f"/api/queue/{item['id']}").status_code == 200


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "authentication"),
        (429, "rate_limit"),
        (408, "timeout"),
        (504, "timeout"),
        (503, "provider_unavailable"),
    ],
)
def test_feedback_categories_redact_keys(status, code):
    class ProviderError(Exception):
        status_code = status

    feedback = error_feedback(
        ProviderError("连接出错 private-test-key"), ModelSettings(api_key="private-test-key")
    )
    assert feedback["code"] == code and "private-test-key" not in feedback["text"]
    assert feedback["action"] and feedback["hint"]


async def test_runtime_stage_tracks_real_source_and_wiki_tool_rounds(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(
            deepwiki_repo="example/project",
            mcp_servers=[McpSettings(id="wiki", name="DeepWiki", url="https://example.com/mcp")],
        )
    )

    @tool
    def mcp_wiki_lookup():
        """界面阶段验收中的本地 Wiki 替身。"""
        return "Program 是入口模块"

    def generate(_self, messages, *_a, **_kw):
        last = messages[-1]
        if getattr(last, "name", "") == "mcp_wiki_lookup":
            answer = AIMessage(content="核对完成。[Program.cs:2](source:Program.cs#L2)")
        elif getattr(last, "name", "") == "read_source":
            answer = AIMessage(
                content="查阅架构",
                tool_calls=[{"name": "mcp_wiki_lookup", "args": {}, "id": "wiki"}],
            )
        else:
            answer = AIMessage(
                content="开始读取",
                tool_calls=[
                    {"name": "read_source", "args": {"path": "Program.cs"}, "id": "source"}
                ],
            )
        return ChatResult(generations=[ChatGeneration(message=answer)])

    async def remote_tools(_self, _servers, emit):
        emit("stage", {"stage": "connecting_mcp", "detail": "本地验收"})
        return [mcp_wiki_lookup]

    monkeypatch.setattr(DeterministicModel, "_generate", generate)
    monkeypatch.setattr("app.runtime.create_model", lambda *_a, **_kw: DeterministicModel())
    monkeypatch.setattr(AgentRuntime, "remote_tools", remote_tools)
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    run = repository.create_run(repository.create_thread("阶段验收")["id"], "核对入口架构", [])
    events = []
    answer = await runtime.execute(run, lambda *event: events.append(event))
    stages = [payload["stage"] for kind, payload in events if kind == "stage"]
    assert answer.startswith("核对完成。[Program.cs:2](source:Program.cs#L2)")
    assert stages[:2] == ["connecting_model", "connecting_mcp"]
    assert "reading_source" in stages and "reading_wiki" in stages
    assert stages.count("generating") == 3 and stages[-1] == "checking_sources"
    assert len([kind for kind, _ in events if kind == "tool_end"]) == 2
