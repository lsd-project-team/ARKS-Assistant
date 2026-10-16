"""只读核对原始列和文件；新增项目元数据单独记录，不输出用户正文。"""

import sys
from pathlib import Path

_SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_SCRIPT_ROOT / "backend"), str(_SCRIPT_ROOT)]

import json
import sqlite3

import httpx
from app.core.config import PROJECT_ROOT

from scripts.verification.data_snapshot import snapshot


def connection(path):
    database = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    database.row_factory = sqlite3.Row
    return database


def columns(database, table):
    return [row[1] for row in database.execute(f'pragma table_info("{table}")')]


def rows(database, table, names):
    selected = ",".join(f'"{name}"' for name in names)
    return [dict(row) for row in database.execute(f'SELECT {selected} FROM "{table}"')]


def encoded(values):
    return sorted(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in values)


def original_tables(before, after):
    tables = [
        row[0]
        for row in before.execute(
            "select name from sqlite_master where type='table' "
            "and name not like 'sqlite_%' and name != 'alembic_version'"
        )
    ]
    result, new_columns, read_changes = {}, {}, 0
    for table in tables:
        names = columns(before, table)
        old_rows, current_rows = rows(before, table, names), rows(after, table, names)
        new_columns[table] = sorted(set(columns(after, table)) - set(names))
        if table == "threads":
            # 浏览器读取可推进已读时间；时间回退或其他旧列改变仍判为失败。
            current_by_id = {row["id"]: row for row in current_rows}
            for old in old_rows:
                current = current_by_id.get(old["id"])
                if current and current.get("last_read_at") != old.get("last_read_at"):
                    read_changes += 1
                    old_time, current_time = (
                        old.get("last_read_at"),
                        current.get("last_read_at"),
                    )
                    if current_time and (not old_time or current_time >= old_time):
                        current["last_read_at"] = old_time
        result[table] = {
            "rows_before": len(old_rows),
            "rows_after": len(current_rows),
            "original_columns_preserved": encoded(old_rows) == encoded(current_rows),
        }
    return result, new_columns, read_changes


def verify():
    output = PROJECT_ROOT / "output"
    baseline = json.loads(
        (output / "answer-quality-data-before-final.json").read_text("utf-8")
    )
    current = snapshot()
    with (
        connection(output / "answer-quality-before-db.sqlite3") as before,
        connection(PROJECT_ROOT / "data/app.sqlite3") as after,
    ):
        tables, added_columns, read_changes = original_tables(before, after)
        revision = after.execute("select version_num from alembic_version").fetchone()[
            0
        ]
        metadata = {
            table: after.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            for table in ("projects", "source_workspaces")
        }
    preserved = {
        name: baseline[name] == current[name]
        for name in ("checkpoints", "files", "settings_sha256")
    }
    with httpx.Client(trust_env=False, timeout=30) as client:
        health = client.get("http://127.0.0.1:8765/api/health").json()
        backup = client.post("http://127.0.0.1:8765/api/backup")
        backup.raise_for_status()
        (output / "answer-quality-backup-delivered.zip").write_bytes(backup.content)
    report = {
        "raw_business_unchanged": baseline["business"] == current["business"],
        "original_tables": tables,
        "added_columns": added_columns,
        "added_project_metadata": metadata,
        "expected_read_timestamp_changes": read_changes,
        "unchanged": preserved,
        "migration": revision,
        "health": health,
        "data_preserved": all(preserved.values())
        and all(table["original_columns_preserved"] for table in tables.values()),
    }
    (output / "answer-quality-data-after-final.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "answer-quality-data-preservation-final.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["data_preserved"]:
        raise SystemExit("原始数据核对未通过，详见验收记录")


if __name__ == "__main__":
    verify()
