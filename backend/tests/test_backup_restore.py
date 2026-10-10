"""备份全链路与失败保护，所有覆盖恢复都发生在测试临时目录。"""

import json
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest
from fastapi.testclient import TestClient

from app.backup import create_backup
from app.backup_restore import restore_backup, restore_journal, rollback_restore
from app.backup_validation import validate_backup
from app.config import AppSettings, ModelSettings, Paths, SettingsStore
from app.main import create_app
from app.process_lock import service_lock
from app.runtime import AgentRuntime
from app.schemas import MemoryWrite
from app.storage import storage_stats
from tests.test_compaction import DeterministicModel


def zip_variant(source, destination, changes=None, omit=()):
    with (
        ZipFile(source) as incoming,
        ZipFile(destination, "w", compression=ZIP_DEFLATED) as outgoing,
    ):
        def write(name, value):
            # Windows 的 ZipInfo 构造器会替换反斜杠；保留恶意原名，才能真实验证拒绝逻辑。
            member = ZipInfo(name)
            member.filename = name
            member.compress_type = ZIP_DEFLATED
            outgoing.writestr(member, value)

        for name in incoming.namelist():
            if name not in omit:
                write(name, (changes or {}).get(name, incoming.read(name)))
        for name, value in (changes or {}).items():
            if name not in incoming.namelist():
                write(name, value)
    return destination


async def test_full_backup_restore_preserves_graph_messages_memory_and_private_settings(
    services, monkeypatch, tmp_path
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings(api_key="dummy-source-private-key")))
    monkeypatch.setattr("app.runtime.create_model", lambda *_args, **_kwargs: DeterministicModel())
    thread = repository.create_thread("恢复完整会话")
    run = repository.create_run(thread["id"], "说明 Program.cs", [])
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    repository.finish(
        run["id"],
        await runtime.execute(
            run, lambda kind, payload: repository.event(run["id"], kind, payload)
        ),
    )
    memories.save(
        MemoryWrite(
            name="恢复事实.md",
            content="入口：Program.cs",
            source_paths=["Program.cs"],
            source_thread_id=thread["id"],
        )
    )
    archive = paths.scratch / "原文档案.md"
    archive.write_text("必须保留的原文\r\n", encoding="utf-8", newline="")
    backup = create_backup(paths)
    preview = validate_backup(backup)
    assert preview["format_version"] == 1 and preview["counts"]["messages"] == 2
    with ZipFile(backup) as zipped:
        assert "settings.private.json" not in zipped.namelist()
        assert "manifest.json" in zipped.namelist()
    target = Paths(tmp_path / "恢复后的 data", paths.workspace)
    target_settings = SettingsStore(target)
    target_settings.save(AppSettings(model=ModelSettings(api_key="dummy-existing-private-key")))
    private_bytes = target_settings.path.read_bytes()
    (target.memories / "旧事实.md").write_bytes(b"old-memory")
    result = restore_backup(backup, target.data)
    assert target_settings.path.read_bytes() == private_bytes
    recovery = Path(result["recovery_directory"])
    assert (recovery / "memories" / "旧事实.md").read_bytes() == b"old-memory"
    assert (target.scratch / archive.name).read_bytes() == archive.read_bytes()
    with TestClient(create_app(target)) as client:
        restored = client.get(f"/api/threads/{thread['id']}").json()
        assert [message["content"] for message in restored["messages"]] == [
            "说明 Program.cs",
            "测试回复",
        ]
        assert client.get(f"/api/threads/{thread['id']}/context").json()["complete"]
        rows = client.get("/api/memories").json()
        assert rows[0]["name"] == "恢复事实.md" and not rows[0]["sources"][0]["stale"]
        assert client.get("/api/memories/project/恢复事实.md/history").json()
        stats = client.get("/api/storage").json()
        assert stats["counts"]["messages"] == 2 and stats["groups"]["recovery"] > 0


@pytest.mark.parametrize(
    "invalid",
    [
        "../escape",
        "memories/../../escape",
        "C:/escape",
        "settings.private.json",
        "memories/NUL.md",
        "memories//a.md",
        "scratch/a/../b",
        "memories\\a.md",
    ],
)
def test_invalid_archive_paths_are_rejected_without_touching_destination(
    services, tmp_path, invalid
):
    paths, _, _, repository, _, _ = services
    repository.create_thread("路径校验")
    bad = zip_variant(create_backup(paths), tmp_path / "bad.zip", {invalid: b"unexpected"})
    target = tmp_path / "target"
    target.mkdir()
    (target / "app.sqlite3").write_bytes(b"original-bytes")
    with pytest.raises(ValueError, match="非法"):
        restore_backup(bad, target)
    assert (target / "app.sqlite3").read_bytes() == b"original-bytes"
    assert not (tmp_path / "escape").exists()


def test_hash_version_legacy_and_truncated_zip_validation(services, tmp_path):
    paths, _, _, repository, memories, _ = services
    repository.create_thread("哈希检查")
    memories.save(MemoryWrite(name="记录.md", content="原文事实"))
    backup = create_backup(paths)
    with ZipFile(backup) as zipped:
        memory_path = next(name for name in zipped.namelist() if name.startswith("memories/"))
        manifest = json.loads(zipped.read("manifest.json"))
    modified = zip_variant(backup, tmp_path / "modified.zip", {memory_path: b"different"})
    with pytest.raises(ValueError, match="哈希"):
        validate_backup(modified)
    manifest["format_version"] = 99
    future = zip_variant(backup, tmp_path / "future.zip", {"manifest.json": json.dumps(manifest)})
    with pytest.raises(ValueError, match="格式版本"):
        validate_backup(future)
    legacy = zip_variant(backup, tmp_path / "legacy.zip", omit=("manifest.json",))
    assert validate_backup(legacy)["format_version"] == 0
    assert validate_backup(legacy)["warnings"]
    truncated = tmp_path / "truncated.zip"
    truncated.write_bytes(backup.read_bytes()[:100])
    with pytest.raises(ValueError, match="ZIP"):
        validate_backup(truncated)


def test_unknown_database_revision_and_broken_foreign_key_are_rejected(services, tmp_path):
    paths, _, _, repository, _, _ = services
    repository.create_thread("数据库校验")
    backup = create_backup(paths)
    with ZipFile(backup) as zipped:
        copy = tmp_path / "app.sqlite3"
        copy.write_bytes(zipped.read("app.sqlite3"))
    # 关闭最后一个连接后，修改才从 WAL 合并到即将打包的数据库文件。
    with closing(sqlite3.connect(copy)) as database, database:
        database.execute("CREATE TABLE alembic_version (version_num TEXT)")
        database.execute("INSERT INTO alembic_version VALUES ('future-unknown')")
    future = zip_variant(
        backup,
        tmp_path / "unknown-db.zip",
        {"app.sqlite3": copy.read_bytes()},
        omit=("manifest.json",),
    )
    with pytest.raises(ValueError, match="数据版本"):
        validate_backup(future)
    with closing(sqlite3.connect(copy)) as database, database:
        database.execute("DROP TABLE alembic_version")
        database.execute(
            "INSERT INTO messages "
            "(id,thread_id,role,content,selections_json,created_at,context_active) "
            "VALUES ('orphan','missing','user','text','[]','now',1)"
        )
    broken = zip_variant(
        backup, tmp_path / "orphan.zip", {"app.sqlite3": copy.read_bytes()}, omit=("manifest.json",)
    )
    with pytest.raises(ValueError, match="关联"):
        validate_backup(broken)


def test_running_service_lock_refuses_restore_and_partial_failure_rolls_back(
    services, tmp_path, monkeypatch
):
    paths, _, _, repository, memories, _ = services
    repository.create_thread("回滚检查")
    memories.save(MemoryWrite(name="新事实.md", content="新数据"))
    backup = create_backup(paths)
    target = tmp_path / "target"
    target.mkdir()
    (target / "app.sqlite3").write_bytes(b"old-database")
    (target / "memories").mkdir()
    (target / "memories" / "old.md").write_bytes(b"old-memory")
    with service_lock(target), pytest.raises(RuntimeError, match="另一个"):
        restore_backup(backup, target)
    original_rename = Path.rename

    failed = False

    def fail_memory_install(path, destination):
        nonlocal failed
        if (
            not failed
            and path.name == "memories"
            and path.parent != target
            and Path(destination) == target / "memories"
        ):
            failed = True
            raise OSError("模拟安装中途失败")
        return original_rename(path, destination)

    monkeypatch.setattr(Path, "rename", fail_memory_install)
    with pytest.raises(ValueError, match="旧数据已回滚"):
        restore_backup(backup, target)
    assert (target / "app.sqlite3").read_bytes() == b"old-database"
    assert (target / "memories" / "old.md").read_bytes() == b"old-memory"
    assert not (target / "restore.pending.json").exists()


def test_interrupted_restore_blocks_startup_until_old_data_is_rolled_back(services, tmp_path):
    paths = services[0]
    target = Paths(tmp_path / "interrupted", paths.workspace)
    recovery = target.data / (".restore-recovery-" + "a" * 32)
    recovery.mkdir()
    (recovery / "app.sqlite3").write_bytes(b"original-database")
    (target.data / "app.sqlite3").write_bytes(b"partly-installed-database")
    (target.memories / "new.md").write_bytes(b"partly-installed-memory")
    restore_journal(target.data, {"recovery": recovery.name, "originals": ["app.sqlite3"]})
    with pytest.raises(RuntimeError, match="未完成"):
        create_app(target)
    assert rollback_restore(target.data)["rolled_back"]
    assert (target.data / "app.sqlite3").read_bytes() == b"original-database"
    assert not target.memories.exists()
    assert (
        recovery / "rejected" / "memories" / "new.md"
    ).read_bytes() == b"partly-installed-memory"


def test_api_backup_validation_storage_and_active_run_guard(services):
    paths = services[0]
    with TestClient(create_app(paths)) as client:
        repository = client.app.state.repository
        thread = repository.create_thread("数据页面")
        queued = repository.create_run(thread["id"], "等待回复", [])
        assert client.post("/api/backup").status_code == 409
        repository.finish(queued["id"], "完成")
        exported = client.post("/api/backup")
        assert exported.status_code == 200
        checked = client.post(
            "/api/backup/validate",
            content=exported.content,
            headers={"Content-Type": "application/zip"},
        )
        assert checked.status_code == 200 and checked.json()["database_revision"] == "0006"
        assert client.post("/api/backup/validate", content=b"invalid").status_code == 409
        stats = client.get("/api/storage").json()
        assert stats["counts"]["messages"] == 2 and stats["groups"]["backups"] > 0
        assert stats["total_bytes"] == sum(stats["groups"].values())


@pytest.mark.skipif(__import__("os").name != "nt", reason="验证 Windows PowerShell 5 恢复入口")
def test_windows_restore_script_handles_chinese_and_spaces(services, tmp_path):
    paths, _, _, repository, _, _ = services
    repository.create_thread("脚本恢复")
    source = create_backup(paths)
    project = Path(__file__).resolve().parents[2]
    target = tmp_path / "中文 数据目录"
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(project / "scripts" / "RestoreData.ps1"),
            "-Backup",
            str(source),
            "-DataDirectory",
            str(target),
            "-Apply",
        ],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert (target / "app.sqlite3").exists()
    assert storage_stats(Paths(target, paths.workspace))["counts"]["threads"] == 1
