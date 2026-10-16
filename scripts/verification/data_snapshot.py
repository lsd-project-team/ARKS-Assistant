"""升级前后的只读数据指纹，输出计数和哈希，不回显用户正文或密钥。"""

import sys
from pathlib import Path

_SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_SCRIPT_ROOT / "backend"), str(_SCRIPT_ROOT)]

import hashlib
import json
import sqlite3
import sys

from app.core.config import PROJECT_ROOT

NEW_COLUMNS = {"source_options_json", "lifecycle"}


def database(path):
    if not path.exists():
        return {}
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type='table' "
                "and name not like 'sqlite_%' and name != 'alembic_version'"
            )
        ]
        result = {}
        for table in tables:
            columns = [
                row[1]
                for row in connection.execute(f'pragma table_info("{table}")')
                if row[1] not in NEW_COLUMNS
            ]
            rows = list(
                connection.execute(
                    "select "
                    + ",".join('"' + column + '"' for column in columns)
                    + f' from "{table}"'
                )
            )
            encoded = sorted(
                json.dumps(
                    row, ensure_ascii=False, default=lambda value: value.hex()
                ).encode()
                for row in rows
            )
            result[table] = {
                "rows": len(rows),
                "sha256": hashlib.sha256(b"\n".join(encoded)).hexdigest(),
            }
        return result


def snapshot():
    data = PROJECT_ROOT / "data"
    return {
        "business": database(data / "app.sqlite3"),
        "checkpoints": database(data / "checkpoints.sqlite3"),
        "files": {
            str(path.relative_to(data)): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ("memories", "scratch")
            for path in (data / folder).rglob("*")
            if path.is_file()
        },
        "settings_sha256": hashlib.sha256(
            (data / "settings.private.json").read_bytes()
        ).hexdigest(),
    }


if __name__ == "__main__":
    destination = (
        PROJECT_ROOT
        / "output"
        / (sys.argv[1] if len(sys.argv) > 1 else "answer-quality-data-before.json")
    )
    report = snapshot()
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print({table: value["rows"] for table, value in report["business"].items()})
