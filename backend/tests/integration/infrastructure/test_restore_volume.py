"""模拟目标卷边界，真实执行备份校验、SQLite恢复与安装失败回滚。"""

import errno
import sqlite3
import stat
from contextlib import closing
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

from app.infrastructure.storage.backup import create_backup
from app.infrastructure.storage.paths import ordinary_path
from app.infrastructure.storage.restore import restore_backup
from app.modules.chat.schemas import MemoryWrite


@pytest.fixture
def volume_backup(services):
    paths, _, _, repository, memories, _ = services
    repository.create_thread("临时数据卷恢复")
    memories.save(MemoryWrite(name="卷内记忆.md", content="保留字节及数据库关联"))
    (paths.scratch / "附件.bin").write_bytes(b"\x00archive\xff\r\n")
    with closing(sqlite3.connect(paths.data / "checkpoints.sqlite3")) as connection, connection:
        connection.execute("CREATE TABLE fixture (content TEXT)")
        connection.execute("INSERT INTO fixture VALUES ('checkpoint')")
    backup = create_backup(paths)
    with ZipFile(backup) as archive:
        expected = {
            name: archive.read(name) for name in archive.namelist() if name != "manifest.json"
        }
    return backup, expected


def preserve_unrelated(target):
    target.mkdir()
    unrelated = target / ".restore-stage-from-another-operation"
    unrelated.mkdir()
    (unrelated / "keep.bin").write_bytes(b"keep-unrelated-stage")
    backups = target / "backups"
    backups.mkdir()
    (backups / "keep.zip").write_bytes(b"keep-existing-backup")
    return unrelated, backups


@pytest.mark.parametrize("with_existing", [False, True])
def test_restore_stages_on_the_target_volume_and_keeps_unrelated_files(
    volume_backup, tmp_path, monkeypatch, with_existing
):
    backup, expected = volume_backup
    target = tmp_path / "mounted-data"
    unrelated, backups = preserve_unrelated(target)
    if with_existing:
        (target / "app.sqlite3").write_bytes(b"old-database")
        (target / "memories").mkdir()
        (target / "memories" / "old.md").write_bytes(b"old-memory")
    rename = Path.rename
    attempted = []

    def rename_on_the_same_device(source, destination):
        original = ordinary_path(source).resolve()
        destination_path = ordinary_path(Path(destination)).resolve()
        # 模拟 /data 为独立挂载点，卷外的实际 rename 由操作系统返回 EXDEV。
        if original.is_relative_to(target) != destination_path.is_relative_to(target):
            raise OSError(errno.EXDEV, "cross-device rename", str(source))
        attempted.append((original, destination_path))
        return rename(source, destination)

    monkeypatch.setattr(Path, "rename", rename_on_the_same_device)
    result = restore_backup(backup, target)
    assert result["restored"] is True and result["counts"]["threads"] == 1
    assert attempted
    for relative, content in expected.items():
        assert (target / relative).read_bytes() == content
    with closing(sqlite3.connect(target / "app.sqlite3")) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    recovery = Path(result["recovery_directory"])
    if with_existing:
        assert (recovery / "app.sqlite3").read_bytes() == b"old-database"
        assert (recovery / "memories" / "old.md").read_bytes() == b"old-memory"
    assert (unrelated / "keep.bin").read_bytes() == b"keep-unrelated-stage"
    assert (backups / "keep.zip").read_bytes() == b"keep-existing-backup"
    assert {entry.name for entry in target.iterdir()} == {
        "app.sqlite3",
        "checkpoints.sqlite3",
        "memories",
        "scratch",
        "service.lock",
        recovery.name,
        unrelated.name,
        backups.name,
    }


def test_install_exdev_rolls_back_and_only_cleans_this_operations_stage(
    volume_backup, tmp_path, monkeypatch
):
    backup, _ = volume_backup
    target = tmp_path / "mounted-data"
    unrelated, backups = preserve_unrelated(target)
    (target / "app.sqlite3").write_bytes(b"old-database")
    (target / "memories").mkdir()
    (target / "memories" / "old.md").write_bytes(b"old-memory")
    rename = Path.rename
    failed = False

    def fail_during_install(source, destination):
        nonlocal failed
        if not failed and source.name == "memories" and Path(destination) == target / "memories":
            failed = True
            raise OSError(errno.EXDEV, "injected device error", str(source))
        return rename(source, destination)

    monkeypatch.setattr(Path, "rename", fail_during_install)
    with pytest.raises(ValueError, match="旧数据已回滚") as error:
        restore_backup(backup, target)
    assert failed and error.value.__cause__.errno == errno.EXDEV
    assert (target / "app.sqlite3").read_bytes() == b"old-database"
    assert (target / "memories" / "old.md").read_bytes() == b"old-memory"
    assert not (target / "checkpoints.sqlite3").exists()
    assert not (target / "scratch").exists()
    assert not (target / "restore.pending.json").exists()
    assert (unrelated / "keep.bin").read_bytes() == b"keep-unrelated-stage"
    assert (backups / "keep.zip").read_bytes() == b"keep-existing-backup"
    assert {entry.name for entry in target.iterdir() if entry.is_dir()} == {
        "memories",
        unrelated.name,
        backups.name,
        next(target.glob(".restore-recovery-*")).name,
    }


def test_pending_restore_refuses_replacement_and_preserves_existing_journal(
    volume_backup, tmp_path
):
    backup, _ = volume_backup
    target = tmp_path / "mounted-data"
    unrelated, backups = preserve_unrelated(target)
    (target / "app.sqlite3").write_bytes(b"partially-restored-database")
    journal = target / "restore.pending.json"
    journal.write_bytes(b'{"recovery":"existing-operation"}')
    with pytest.raises(ValueError, match="未完成的恢复"):
        restore_backup(backup, target)
    assert (target / "app.sqlite3").read_bytes() == b"partially-restored-database"
    assert journal.read_bytes() == b'{"recovery":"existing-operation"}'
    assert {entry.name for entry in target.iterdir()} == {
        "app.sqlite3",
        "restore.pending.json",
        "service.lock",
        unrelated.name,
        backups.name,
    }


@pytest.mark.parametrize("kind", ["symlink", "case_collision", "escape"])
def test_untrusted_zip_cannot_escape_volume_stage_or_replace_existing_data(
    volume_backup, tmp_path, kind
):
    backup, _ = volume_backup
    bad = tmp_path / "untrusted.zip"
    with ZipFile(backup) as incoming, ZipFile(bad, "w") as outgoing:
        for name in incoming.namelist():
            outgoing.writestr(name, incoming.read(name))
        if kind == "symlink":
            link = ZipInfo("scratch/link")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            outgoing.writestr(link, "../../outside")
        elif kind == "case_collision":
            outgoing.writestr("scratch/DATA.txt", b"first")
            outgoing.writestr("scratch/data.txt", b"collision")
        else:
            outgoing.writestr("scratch/../../outside", b"escape")
    target = tmp_path / "mounted-data"
    unrelated, backups = preserve_unrelated(target)
    (target / "app.sqlite3").write_bytes(b"old-database")
    with pytest.raises(ValueError, match="非法|冲突"):
        restore_backup(bad, target)
    assert (target / "app.sqlite3").read_bytes() == b"old-database"
    assert not (tmp_path / "outside").exists()
    assert not (target / "restore.pending.json").exists()
    assert {entry.name for entry in target.iterdir()} == {
        "app.sqlite3",
        unrelated.name,
        backups.name,
    }
