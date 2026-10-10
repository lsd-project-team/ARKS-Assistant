"""清理预览与竞态保护，覆盖回收站恢复和跨工作区隔离。"""

import pytest
from fastapi.testclient import TestClient

from app.conversation_cleanup import EmptyConversations
from app.main import create_app
from app.models import QueuedQuestion, Thread
from app.repository import Repository
from app.schemas import MemoryWrite


def test_preview_excludes_messages_runs_queue_pin_memory_archive_and_other_workspace(services):
    _, database, _, repository, memories, _ = services
    empty = repository.create_thread("真正的空会话")
    populated = repository.create_thread("有消息")
    run = repository.create_run(populated["id"], "原问题", [])
    repository.finish(run["id"], "原回答")
    queued = repository.create_thread("等待问题")
    with database.session.begin() as session:
        session.add(QueuedQuestion(thread_id=queued["id"], content="等会再问"))
    pinned = repository.create_thread("置顶")
    repository.catalog.pin(pinned["id"], True)
    remembered = repository.create_thread("已有来源记忆")
    memories.save(
        MemoryWrite(name="关联记忆.md", content="保留事实", source_thread_id=remembered["id"])
    )
    archived = repository.create_thread("归档")
    repository.catalog.change(archived["id"], "archived")
    Repository(database, "other-workspace").create_thread("其他工作区")
    preview = EmptyConversations(repository).preview()
    assert preview["total"] == 1 and [row["id"] for row in preview["threads"]] == [empty["id"]]


def test_preview_change_is_atomic_and_batch_can_be_restored(services):
    repository = services[3]
    cleanup = EmptyConversations(repository)
    first, second = [repository.create_thread("新对话") for _ in range(2)]
    versions = {row["id"]: row["updated_at"] for row in cleanup.preview()["threads"]}
    run = repository.create_run(second["id"], "预览后首次发送", [])
    repository.finish(run["id"], "完整回答")
    with pytest.raises(ValueError, match="没有整理"):
        cleanup.change(versions)
    assert repository.catalog.get(first["id"])["state"] == "active"
    assert len(repository.thread(second["id"])["messages"]) == 2
    trashed = cleanup.change({first["id"]: first["updated_at"]})
    with pytest.raises(FileNotFoundError):
        repository.thread(first["id"])
    restored = cleanup.change({first["id"]: trashed["version"]}, restore=True)
    assert restored["ids"] == [first["id"]]
    assert repository.thread(first["id"])["messages"] == []
    with pytest.raises(ValueError):
        cleanup.change({first["id"]: trashed["version"]}, restore=True)


def test_cleanup_api_routes_versions_and_pin_race(services):
    with TestClient(create_app(services[0])) as client:
        repository = client.app.state.repository
        first = repository.create_thread("未开始")
        preview = client.get("/api/threads/empty").json()
        assert preview["total"] == 1
        payload = {"versions": {first["id"]: preview["threads"][0]["updated_at"]}}
        repository.catalog.pin(first["id"], True)
        assert client.post("/api/threads/empty/trash", json=payload).status_code == 409
        repository.catalog.pin(first["id"], False)
        result = client.post("/api/threads/empty/trash", json=payload)
        assert result.status_code == 200
        assert client.get("/api/threads?state=deleted").json()[0]["id"] == first["id"]
        restore = {"versions": {first["id"]: result.json()["version"]}}
        assert client.post("/api/threads/empty/restore", json=restore).status_code == 200
        assert client.post("/api/threads/empty/trash", json={"versions": {}}).status_code == 422
        with services[1].session() as session:
            assert session.get(Thread, first["id"]).state == "active"
