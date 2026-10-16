import asyncio

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy import func, select

from app.conversation_lifecycle import ConversationLifecycle
from app.main import create_app
from app.models import Message, Run, RunEvent, Thread
from app.runs import RunManager
from app.schemas import MemoryWrite
from app.services import AppServices
from tests.api_paths import project_api


def test_archive_trash_restore_pin_and_unread(services):
    repository = services[3]
    first = repository.create_thread("新对话")
    second = repository.create_thread("另一个对话")
    run = repository.create_run(first["id"], "解释源码入口", [])
    repository.finish(run["id"], "入口位于 Main")
    assert repository.catalog.get(first["id"])["title"] == "解释源码入口"
    assert repository.threads()[0]["has_unread"]
    repository.catalog.mark_read(first["id"])
    assert not repository.threads()[0]["has_unread"]
    repository.catalog.pin(second["id"], True)
    repository.catalog.pin(first["id"], True)
    repository.catalog.reorder([first["id"], second["id"]])
    assert [row["id"] for row in repository.threads()] == [first["id"], second["id"]]
    with pytest.raises(ValueError):
        repository.catalog.reorder([first["id"]])
    repository.catalog.change(first["id"], "archived")
    assert [row["id"] for row in repository.threads("archived")] == [first["id"]]
    repository.catalog.change(first["id"], "deleted")
    with pytest.raises(FileNotFoundError):
        repository.create_run(first["id"], "不能继续已删除会话", [])
    assert len(repository.threads("deleted")) == 1
    repository.catalog.change(first["id"], "active")
    assert len(repository.thread(first["id"])["messages"]) == 2
    repository.rename(first["id"], "手动标题")
    assert repository.catalog.get(first["id"])["auto_title"] is False


def test_search_matches_body_selection_path_and_literal_wildcards(services):
    repository = services[3]
    thread = repository.create_thread("标题不含查询词")
    run = repository.create_run(
        thread["id"],
        "正文标记 a%b",
        [{"path": "Module/Hidden.cs", "content": "void SelectionOnly() {}"}],
    )
    repository.finish(run["id"], "解释结果")
    for query in ("正文标记", "SelectionOnly", "Hidden.cs", "a%b"):
        rows = repository.threads(query=query)
        assert rows[0]["matched_message_id"] == run["message_id"]
        assert query in rows[0]["snippet"]
    assert repository.threads(query="a_b") == []
    repository.catalog.change(thread["id"], "deleted")
    assert repository.threads(query="SelectionOnly") == []
    assert repository.threads("deleted", "SelectionOnly")


async def test_trash_stops_active_reply_and_purge_cleans_checkpoints_and_preserves_memory(
    services,
):
    paths, database, workspace, repository, memories, settings = services

    class WaitingRuntime:
        async def execute(self, _run, emit):
            emit("token", {"text": "部分答案"})
            await asyncio.Event().wait()

    runtime = WaitingRuntime()
    manager = RunManager(repository, runtime, settings)
    services_object = AppServices(
        paths, settings, database, workspace, repository, memories, runtime, manager
    )
    lifecycle = ConversationLifecycle(services_object)
    thread = repository.create_thread("删除测试")
    run = repository.create_run(thread["id"], "问题", [])
    memories.save(
        MemoryWrite(name="持久事实.md", content="保留独立记忆", source_thread_id=thread["id"])
    )
    session_id = "session_" + "a" * 32
    async with AsyncSqliteSaver.from_conn_string(str(paths.data / "checkpoints.sqlite3")) as saver:
        from app.runtime import AgentRuntime

        agent = AgentRuntime(paths, settings, workspace, repository, memories)
        graph = await agent.graph(thread["id"], saver, lambda *_: None, inspection=True)
        await graph.aupdate_state(
            {"configurable": {"thread_id": thread["id"]}},
            {"messages": [HumanMessage(content="快照")], "_summarization_session_id": session_id},
            as_node="model",
        )
    old_archive = paths.scratch / "conversation_history" / f"{session_id}.md"
    old_archive.parent.mkdir()
    old_archive.write_text("旧版归属档案", encoding="utf-8")
    artifacts = paths.scratch / "threads" / thread["id"]
    artifacts.mkdir(parents=True)
    (artifacts / "history.md").write_text("新版归属档案", encoding="utf-8")
    manager.start(run)
    await asyncio.sleep(0.02)
    await lifecycle.trash(thread["id"])
    assert not manager.tasks
    assert repository.threads("deleted")[0]["latest_status"] == "cancelled"
    assert memories.read("project", "持久事实.md")["source_thread_status"] == "deleted"
    await lifecycle.purge(thread["id"])
    with database.session() as session:
        for model in (Thread, Message, Run, RunEvent):
            assert session.scalar(select(func.count()).select_from(model)) == 0
    async with AsyncSqliteSaver.from_conn_string(str(paths.data / "checkpoints.sqlite3")) as saver:
        assert await saver.aget_tuple({"configurable": {"thread_id": thread["id"]}}) is None
    assert not artifacts.exists() and not old_archive.exists()
    assert memories.read("project", "持久事实.md")["content"] == "保留独立记忆"


def test_management_api_and_workspace_scope(services):
    with TestClient(create_app(services[0])) as client:
        thread = client.post(project_api(client, "/threads"), json={}).json()
        identifier = thread["id"]
        response = client.patch(
            project_api(client, f"/threads/{identifier}"), json={"pinned": True}
        )
        assert response.json()["pinned_order"] is not None
        assert (
            client.patch(
                project_api(client, f"/threads/{identifier}"), json={"title": "  "}
            ).status_code
            == 422
        )
        assert (
            client.patch(
                project_api(client, f"/threads/{identifier}"), json={"state": "archived"}
            ).status_code
            == 200
        )
        assert len(client.get(project_api(client, "/threads?state=archived")).json()) == 1
        assert client.delete(project_api(client, f"/threads/{identifier}")).status_code == 200
        assert client.get(project_api(client, f"/threads/{identifier}")).status_code == 404
        assert client.post(project_api(client, f"/threads/{identifier}/restore")).status_code == 200
        assert (
            client.delete(project_api(client, f"/threads/{identifier}/permanent")).status_code
            == 409
        )
        assert client.delete(project_api(client, "/threads/missing")).status_code == 404


def test_first_send_validation_and_export(services, monkeypatch):
    async def answer(*_args):
        return "自动检查回复"

    monkeypatch.setattr("app.runtime.AgentRuntime.execute", answer)
    with TestClient(create_app(services[0])) as client:
        assert (
            client.post(project_api(client, "/threads/start"), json={"content": "  "}).status_code
            == 422
        )
        assert client.get(project_api(client, "/threads")).json() == []
        result = client.post(
            project_api(client, "/threads/start"), json={"content": "  首次发送  "}
        )
        assert result.status_code == 201
        identifier = result.json()["thread_id"]
        assert (
            client.get(project_api(client, f"/threads/{identifier}")).json()["title"] == "首次发送"
        )
        exported = client.get(
            project_api(client, f"/threads/{identifier}/export?format=json")
        ).json()
        assert exported["schema_version"] == 1
        assert exported["conversation"]["messages"][0]["content"] == "首次发送"
        assert "首次发送" in client.get(project_api(client, f"/threads/{identifier}/export")).text
