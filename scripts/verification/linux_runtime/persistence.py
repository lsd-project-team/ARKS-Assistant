"""临时SQLite一致性、在线备份及异地恢复。"""

import sqlite3
from contextlib import closing
from zipfile import ZipFile

from .http_checks import request
from .safety import owns, require


def database_integrity(data):
    file = data / "app.sqlite3"
    with closing(sqlite3.connect(f"file:{file.as_posix()}?mode=ro", uri=True)) as connection:
        require(
            connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
            "sqlite_integrity_failed",
        )
        require(
            connection.execute("PRAGMA foreign_key_check").fetchall() == [],
            "sqlite_foreign_keys_failed",
        )
        require(connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal", "sqlite_not_wal")
        for table in ("accounts", "projects", "code_changes", "handover_records", "handover_blobs"):
            require(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] > 0,
                "sqlite_fixture_rows_missing",
            )
        for table in ("runs", "project_reading_jobs", "code_verifications"):
            require(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0,
                "unexpected_agent_or_verification_execution",
            )


def online_backup(client, root, token):
    owns(root, token)
    response = request(client, "POST", "/api/backup")
    require(0 < len(response.content) < 32 * 1024 * 1024, "fixture_backup_size_invalid")
    archive = root / "backup.zip"
    archive.write_bytes(response.content)
    with ZipFile(archive) as backup:
        names = set(backup.namelist())
        require({"app.sqlite3", "manifest.json"} <= names, "backup_database_missing")
        require(
            "settings.private.json" not in names and "auth.initial-accounts.json" not in names,
            "backup_contains_private_configuration",
        )
        require(
            any(name.startswith("scratch/code-changes/") for name in names),
            "backup_isolated_copy_missing",
        )
    return archive


def restore(archive, root, token, target=None, target_token=None):
    from app.infrastructure.storage.restore import restore_backup

    owns(root, token)
    if target is None:
        target = root / "restored-data"
        require(not target.exists(), "restore_target_not_empty")
    else:
        owns(target, target_token)
    result = restore_backup(archive, target)
    require(result.get("restored") is True, "fixture_restore_failed")
    database_integrity(target)
    return target
