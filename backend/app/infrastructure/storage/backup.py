"""在线备份通过 SQLite backup API，避免 WAL 数据遗漏。"""

import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.core.config import Paths, dump_json
from app.infrastructure.storage.manifest import manifest_for


def create_backup(paths: Paths) -> Path:
    folder = paths.data / "backups"
    folder.mkdir(exist_ok=True)
    destination = folder / f"trunk-agent-{datetime.now():%Y%m%d-%H%M%S-%f}.zip"
    partial = destination.with_suffix(".partial")
    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary)
        try:
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
            # 密钥配置不进入导出备份；恢复后通过设置页重新填写。
            for group in ("memories", "scratch", "instructions"):
                for file in (paths.data / group).rglob("*"):
                    if group == "instructions" and file.name != "agent.md":
                        continue
                    if file.is_file():
                        if file.is_symlink() or not file.resolve().is_relative_to(paths.data):
                            raise ValueError("备份资料包含越界链接，请先核对资料目录")
                        target = staging / file.relative_to(paths.data)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(file, target)
            manifest = manifest_for(staging, paths.workspace, datetime.now(UTC).isoformat())
            (staging / "manifest.json").write_text(dump_json(manifest), encoding="utf-8")
            with ZipFile(partial, "w", compression=ZIP_DEFLATED) as archive:
                for file in staging.rglob("*"):
                    if file.is_file():
                        archive.write(file, file.relative_to(staging))
            partial.replace(destination)
        finally:
            partial.unlink(missing_ok=True)
    return destination
