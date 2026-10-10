import asyncio
from concurrent.futures import ThreadPoolExecutor
from zipfile import ZipFile

import pytest

from app.backup import create_backup
from app.config import AppSettings, ModelSettings
from app.database import Database
from app.memory import MemoryService
from app.repository import Repository
from app.schemas import MemoryWrite


def test_archive_events_and_restart_recovery(services):
    paths, database, workspace, repository, _, _ = services
    thread = repository.create_thread("持久化测试")
    run = repository.create_run(thread["id"], "原始问题", [])
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(
            pool.map(
                lambda index: repository.event(run["id"], "notice", {"index": index}), range(20)
            )
        )
    sequences = [event["sequence"] for event in repository.events(run["id"])]
    assert sequences == list(range(1, 21))
    assert repository.events(run["id"], 15)[0]["sequence"] == 16
    with pytest.raises(ValueError):
        repository.create_run(thread["id"], "同时运行", [])
    database.close()
    reopened = Database(paths.data / "app.sqlite3")
    restored = Repository(reopened, workspace.id)
    restored.recover()
    assert restored.run(run["id"])["status"] == "interrupted"
    resumed = restored.resume(run["id"])
    assert resumed["message_id"] == run["message_id"]
    assert len(restored.thread(thread["id"])["messages"]) == 1
    reopened.close()


def test_memory_versions_provenance_and_reload(services):
    paths, database, workspace, repository, memory, _ = services
    thread = repository.create_thread("来源")
    request = MemoryWrite(
        name="项目.md",
        content="入口在 Program.cs",
        source_paths=["Program.cs"],
        source_thread_id=thread["id"],
    )
    saved = memory.save(request)
    with pytest.raises(ValueError):
        memory.save(request)
    reloaded = MemoryService(paths, database, workspace)
    assert reloaded.read("project", "项目.md")["source_thread_id"] == thread["id"]
    (workspace.root / "Program.cs").write_text("class Changed {}", encoding="utf-8")
    assert reloaded.read("project", "项目.md")["sources"][0]["stale"]
    reloaded.delete("project", "项目.md", saved["version"])
    assert reloaded.list() == []


def test_secret_mask_and_backup(services):
    paths, _, _, repository, _, settings = services
    config = AppSettings(model=ModelSettings(api_key="TEST-SECRET"))
    settings.save(config)
    public = settings.public()
    assert "TEST-SECRET" not in str(public)
    public["model"]["model"] = "changed"
    settings.save(AppSettings.model_validate(public))
    assert settings.load().model.api_key == "TEST-SECRET"
    repository.create_thread("备份")
    with ZipFile(create_backup(paths)) as archive:
        assert "app.sqlite3" in archive.namelist()
        assert "settings.private.json" not in archive.namelist()


@pytest.mark.asyncio
async def test_cancel_does_not_corrupt_history(services):
    from app.runs import RunManager

    class WaitingRuntime:
        async def execute(self, _run, emit):
            emit("token", {"text": "部分回复"})
            await asyncio.Event().wait()

    repository, settings = services[3], services[5]
    manager = RunManager(repository, WaitingRuntime(), settings)
    thread = repository.create_thread("取消")
    run = repository.create_run(thread["id"], "问题", [])
    manager.start(run)
    await asyncio.sleep(0.02)
    await manager.cancel(run["id"])
    assert repository.run(run["id"])["status"] == "cancelled"
    assert repository.run(run["id"])["answer"] == "部分回复"
    assert len(repository.thread(thread["id"])["messages"]) == 1
