"""记忆检索、冲突确认与可恢复版本的功能回归。"""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.main import create_app
from app.memory import MemoryService
from app.runtime import AgentRuntime
from app.schemas import MemoryRestore, MemoryWrite
from tests.api_paths import project_api
from tests.test_compaction import DeterministicModel


def test_relevance_preferences_and_duplicate_injection(services):
    memory = services[4]
    memory.save(MemoryWrite(name="无关.md", content="数据库使用 SQLite 存储对话"))
    memory.save(MemoryWrite(name="入口.md", content="Program.cs 内 Main 启动 WinForms"))
    memory.save(MemoryWrite(name="偏好.md", scope="user", content="回答使用简洁中文"))
    prompt, included = memory.prompt_snapshot("请解释 Program.cs 的 Main")
    assert [row["name"] for row in included] == ["偏好.md", "入口.md"]
    assert included[0]["inclusion_reason"] == "稳定用户偏好"
    assert "SQLite" not in prompt
    assert memory.prompt_snapshot("你好，今天心情如何")[1][0]["name"] == "偏好.md"
    assert len(memory.prompt_snapshot("你好，今天心情如何")[1]) == 1
    # 旧版本或手工添加的重复文件也不重复注入。
    (memory.folder("project") / "旧重复.md").write_text("回答使用简洁中文", encoding="utf-8")
    assert memory.prompt_snapshot()[0].count("回答使用简洁中文") == 1


def test_duplicate_and_conflicting_facts_need_current_review(services):
    memory = services[4]
    first = memory.save(MemoryWrite(name="入口.md", content="入口文件：Program.cs"))
    duplicate = MemoryWrite(name="重复.md", content="入口文件： Program.cs \n")
    assert memory.review(duplicate)[0]["kind"] == "duplicate"
    with pytest.raises(ValueError, match="已保存在"):
        memory.save(duplicate)
    alternate = MemoryWrite(name="入口说明.md", content="入口文件：Other.cs")
    assert memory.review(alternate)[0]["kind"] == "conflict"
    with pytest.raises(ValueError, match="核对"):
        memory.save(alternate)
    acknowledged = alternate.model_copy(
        update={
            "confirm_conflicts": True,
            "reviewed_versions": {"入口.md": first["version"]},
        }
    )
    changed = memory.save(
        MemoryWrite(name="入口.md", content="入口文件：Changed.cs", version=first["version"])
    )
    with pytest.raises(ValueError, match="相关记忆已更新"):
        memory.save(acknowledged)
    acknowledged.reviewed_versions = {"入口.md": changed["version"]}
    assert memory.save(acknowledged)["name"] == "入口说明.md"
    prompt, selected = memory.prompt_snapshot("入口文件在哪里")
    assert "同字段不同值" in prompt and all(row["conflicts"] for row in selected)
    assert not (memory.folder("project") / "重复.md").exists()


def test_history_restore_delete_and_source_snapshot_survive_restart(services):
    paths, database, workspace, repository, memory, _ = services
    thread = repository.create_thread("事实来源")
    original = "入口位于 Program.cs\r\n需要核对行号\r\n"
    first = memory.save(
        MemoryWrite(
            name="事实.md",
            content=original,
            source_paths=["Program.cs"],
            source_thread_id=thread["id"],
        )
    )
    second = memory.save(
        MemoryWrite(name="事实.md", content="修改后的事实", version=first["version"])
    )
    history = memory.history.list("project", "事实.md")
    assert [row["action"] for row in history] == ["updated", "created"]
    assert history[-1]["content"] == original
    (workspace.root / "Program.cs").write_text("class Changed {}", encoding="utf-8")
    restored = memory.restore(
        "project",
        "事实.md",
        MemoryRestore(
            revision_id=history[-1]["id"],
            version=second["version"],
        ),
    )
    assert restored["sources"][0]["stale"]
    assert restored["sources"][0]["version"] == first["sources"][0]["version"]
    assert restored["source_thread_id"] == thread["id"]
    assert (memory.folder("project") / "事实.md").read_bytes() == original.encode()
    memory.delete("project", "事实.md", restored["version"])
    reopened = MemoryService(paths, database, workspace)
    assert reopened.list() == []
    assert reopened.list(True)[0]["deleted"]
    assert reopened.prompt() == ""
    revision = reopened.history.list("project", "事实.md")[0]
    restored = reopened.restore("project", "事实.md", MemoryRestore(revision_id=revision["id"]))
    assert restored["content"] == original
    assert not reopened.list(True)[0].get("deleted")
    with pytest.raises(ValueError, match="已被更新"):
        reopened.restore("project", "事实.md", MemoryRestore(revision_id=revision["id"]))


def test_legacy_first_edit_preserves_original_and_history_scope(services):
    memory = services[4]
    (memory.folder("project") / "旧记忆.md").write_bytes("原有事实".encode())
    original = memory.read("project", "旧记忆.md")
    memory.save(MemoryWrite(name="旧记忆.md", content="新事实", version=original["version"]))
    history = memory.history.list("project", "旧记忆.md")
    assert history[-1]["action"] == "imported" and history[-1]["content"] == "原有事实"
    with pytest.raises(FileNotFoundError):
        memory.restore("user", "旧记忆.md", MemoryRestore(revision_id=history[-1]["id"]))
    assert memory.history.list("user", "旧记忆.md") == []


def test_concurrent_identical_content_does_not_create_duplicates(services):
    memory = services[4]

    def create(name):
        try:
            return memory.save(MemoryWrite(name=name, content="相同持久事实"))
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, ["甲.md", "乙.md"]))
    assert sum(result is not None for result in results) == 1
    assert len(memory.list()) == 1


def test_memory_api_review_history_and_recovery(services):
    with TestClient(create_app(services[0])) as client:
        first = client.put(
            project_api(client, "/memories"), json={"name": "偏好.md", "content": "简洁中文"}
        ).json()
        matches = client.post(
            project_api(client, "/memories/review"), json={"name": "重复.md", "content": "简洁中文"}
        )
        assert matches.json()[0]["kind"] == "duplicate"
        assert (
            client.put(
                project_api(client, "/memories"), json={"name": "重复.md", "content": "简洁中文"}
            ).status_code
            == 409
        )
        history = client.get(project_api(client, "/memories/project/偏好.md/history")).json()
        assert len(history) == 1
        assert (
            client.delete(
                project_api(client, f"/memories/project/偏好.md?version={first['version']}")
            ).status_code
            == 200
        )
        assert client.get(project_api(client, "/memories")).json() == []
        assert client.get(project_api(client, "/memories?include_deleted=true")).json()[0][
            "deleted"
        ]
        assert (
            client.post(
                project_api(client, "/memories/project/偏好.md/restore"),
                json={
                    "revision_id": history[0]["id"],
                    "version": None,
                },
            ).json()["content"]
            == "简洁中文"
        )
        assert client.get(project_api(client, "/memories/user/偏好.md/history")).json() == []


async def test_runtime_records_only_selected_memory_snapshot(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    memories.save(MemoryWrite(name="入口.md", content="Program.cs 中的 Main 启动窗口"))
    memories.save(MemoryWrite(name="无关.md", content="数据库中保存会话档案"))
    memories.save(MemoryWrite(name="偏好.md", scope="user", content="使用中文简短回答"))
    monkeypatch.setattr("app.runtime.create_model", lambda *_args, **_kwargs: DeterministicModel())
    thread = repository.create_thread("相关记忆")
    run = repository.create_run(thread["id"], "解释 Program.cs 的 Main", [])
    events = []
    await AgentRuntime(paths, settings, workspace, repository, memories).execute(
        run, lambda kind, payload: events.append((kind, payload))
    )
    snapshot = next(payload["memories"] for kind, payload in events if kind == "context_sources")
    assert [row["name"] for row in snapshot] == ["偏好.md", "入口.md"]


def test_file_and_history_roll_back_when_database_commit_fails(services):
    _, database, _, _, memory, _ = services
    first = memory.save(MemoryWrite(name="事务.md", content="原始内容"))
    target = memory.folder("project") / "事务.md"
    observed = []

    def reject(_session):
        observed.append(target.read_bytes() if target.exists() else None)
        raise RuntimeError("模拟提交失败")

    event.listen(database.session.class_, "before_commit", reject)
    try:
        with pytest.raises(RuntimeError, match="提交失败"):
            memory.save(MemoryWrite(name="事务.md", content="修改内容", version=first["version"]))
        assert observed[-1] == "修改内容".encode()
        assert target.read_bytes() == "原始内容".encode()
        with pytest.raises(RuntimeError, match="提交失败"):
            memory.delete("project", "事务.md", first["version"])
        assert observed[-1] is None and target.read_bytes() == "原始内容".encode()
        with pytest.raises(RuntimeError, match="提交失败"):
            memory.save(MemoryWrite(name="新建事务.md", content="新内容"))
        assert not (target.parent / "新建事务.md").exists()
    finally:
        event.remove(database.session.class_, "before_commit", reject)
    assert len(memory.history.list("project", "事务.md")) == 1
    assert memory.read("project", "事务.md")["version"] == first["version"]
