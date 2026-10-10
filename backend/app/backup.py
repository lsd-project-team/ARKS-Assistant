"""在线备份通过 SQLite backup API，避免 WAL 数据遗漏。"""

import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.config import Paths


def create_backup(paths: Paths) -> Path:
    folder = paths.data / "backups"
    folder.mkdir(exist_ok=True)
    destination = folder / f"trunk-agent-{datetime.now():%Y%m%d-%H%M%S-%f}.zip"
    with tempfile.TemporaryDirectory() as temporary:
        with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
            for name in ("app.sqlite3", "checkpoints.sqlite3"):
                original = paths.data / name
                if not original.exists():
                    continue
                copy = Path(temporary) / name
                with (
                    closing(sqlite3.connect(original)) as source,
                    closing(sqlite3.connect(copy)) as target,
                ):
                    source.backup(target)
                archive.write(copy, name)
            # 密钥配置不进入导出备份；恢复后通过设置页重新填写。
            for group in ("memories", "scratch"):
                for file in (paths.data / group).rglob("*"):
                    if file.is_file():
                        archive.write(file, file.relative_to(paths.data))
    return destination
