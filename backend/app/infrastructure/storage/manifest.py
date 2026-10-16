"""备份格式与数据库校验共享元数据，预览只返回数量和版本。"""

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

from app.infrastructure.storage.paths import ordinary_path

FORMAT_VERSION = 1
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_EXPANDED_BYTES = 2 * 1024 * 1024 * 1024


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def database_info(
    path: Path, *, business: bool = False, verify: bool = True, immutable: bool = True
) -> dict:
    try:
        uri = ordinary_path(path).as_uri() + "?mode=ro" + ("&immutable=1" if immutable else "")
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute("PRAGMA trusted_schema=OFF")
            if verify and connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise ValueError("备份数据库完整性检查未通过")
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if business:
                expected = {
                    "threads": {"id", "workspace_id", "title"},
                    "messages": {"id", "thread_id", "content", "selections_json"},
                    "runs": {"id", "thread_id", "message_id", "status"},
                }
                for table, required in expected.items():
                    if table not in tables or not required <= {
                        row[1] for row in connection.execute(f"PRAGMA table_info({table})")
                    }:
                        raise ValueError("备份的业务数据库结构不受支持")
                if verify and connection.execute("PRAGMA foreign_key_check").fetchone():
                    raise ValueError("备份数据库存在失效的关联记录")
            counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("threads", "messages", "runs", "memory_revisions", "checkpoints")
                if table in tables
            }
            revision = (
                connection.execute("SELECT version_num FROM alembic_version").fetchone()
                if "alembic_version" in tables
                else None
            )
            return {"revision": revision[0] if revision else None, "counts": counts}
    except sqlite3.DatabaseError as error:
        raise ValueError("备份数据库无法读取或结构不受支持") from error


def manifest_for(folder: Path, workspace: Path, created_at: str) -> dict:
    business = database_info(folder / "app.sqlite3", business=True)
    files = {
        file.relative_to(folder).as_posix(): {
            "bytes": file.stat().st_size,
            "sha256": file_hash(file),
        }
        for file in folder.rglob("*")
        if file.is_file()
    }
    return {
        "format_version": FORMAT_VERSION,
        "created_at": created_at,
        "workspace_root": str(workspace),
        "database_revision": business["revision"],
        "counts": business["counts"],
        "files": files,
        "includes_private_settings": False,
    }
