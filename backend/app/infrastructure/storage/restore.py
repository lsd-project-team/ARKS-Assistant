"""停服后的恢复入口：先校验，在同一磁盘暂存，失败时归还旧文件。"""

import argparse
import json
import re
import uuid
from pathlib import Path

from app.core.process_lock import service_lock
from app.infrastructure.storage.validation import checked_backup, validate_backup

DATA_NAMES = ("app.sqlite3", "checkpoints.sqlite3", "memories", "scratch")
RELATED_NAMES = (
    *DATA_NAMES,
    "app.sqlite3-wal",
    "app.sqlite3-shm",
    "checkpoints.sqlite3-wal",
    "checkpoints.sqlite3-shm",
)


def restore_journal(destination: Path, value: dict):
    temporary = destination / "restore.pending.tmp"
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(destination / "restore.pending.json")


def rollback_restore(destination: Path) -> dict:
    destination = destination.resolve()
    journal = destination / "restore.pending.json"
    with service_lock(destination):
        try:
            value = json.loads(journal.read_text(encoding="utf-8"))
            name = value["recovery"]
            originals = value["originals"]
            if not re.fullmatch(r"\.restore-recovery-[a-f0-9]{32}", name) or not (
                isinstance(originals, list) and set(originals) <= set(RELATED_NAMES)
            ):
                raise ValueError("恢复日志不受支持，不能自动回滚")
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("无法读取待恢复日志，请核对数据目录") from error
        recovery = destination / name
        if recovery.is_symlink() or recovery.resolve().parent != destination:
            raise ValueError("恢复目录超出数据目录")
        rejected = recovery / "rejected"
        rejected.mkdir(exist_ok=True)
        for name in RELATED_NAMES:
            current, original = destination / name, recovery / name
            if any(
                path.is_symlink() or not path.resolve().is_relative_to(destination)
                for path in (current, original)
            ):
                raise ValueError("回滚目标包含越界链接")
            if original.exists():
                if current.exists():
                    current.rename(rejected / name)
                original.rename(current)
            elif name not in originals and current.exists():
                current.rename(rejected / name)
        journal.unlink()
        return {"rolled_back": True, "recovery_directory": str(recovery)}


def restore_backup(source: Path, destination: Path) -> dict:
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    # 校验与解压始终在隔离目录完成；获得服务锁后才触碰现有数据。
    with checked_backup(source, temporary_parent=destination.parent) as (report, staged):
        with service_lock(destination):
            if (destination / "restore.pending.json").exists():
                raise ValueError("存在未完成的恢复，请先使用 --rollback 回滚")
            for name in RELATED_NAMES:
                target = destination / name
                if target.is_symlink() or not target.resolve().is_relative_to(destination):
                    raise ValueError("现有数据目录包含越界链接，不能自动替换")
            recovery = destination / f".restore-recovery-{uuid.uuid4().hex}"
            recovery.mkdir()
            restore_journal(
                destination,
                {
                    "recovery": recovery.name,
                    "originals": [name for name in RELATED_NAMES if (destination / name).exists()],
                },
            )
            moved, installed = [], []
            try:
                for name in RELATED_NAMES:
                    target = destination / name
                    if target.exists():
                        target.rename(recovery / name)
                        moved.append(name)
                for name in DATA_NAMES:
                    incoming = staged / name
                    if incoming.exists():
                        incoming.rename(destination / name)
                        installed.append(name)
            except OSError as error:
                # 新文件也移回暂存目录；旧文件保持字节不变，避免不完整恢复留在原位置。
                for name in reversed(installed):
                    (destination / name).rename(staged / name)
                for name in reversed(moved):
                    (recovery / name).rename(destination / name)
                (destination / "restore.pending.json").unlink()
                raise ValueError("恢复失败，旧数据已回滚；请检查文件占用和磁盘空间") from error
            (destination / "restore.pending.json").unlink()
            return {
                **report,
                "restored": True,
                "recovery_directory": str(recovery),
                "data_directory": str(destination),
            }


def main():
    parser = argparse.ArgumentParser(description="Trunk Agent 本地备份校验与停服恢复")
    parser.add_argument("backup", type=Path, nargs="?")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    arguments = parser.parse_args()
    if (arguments.apply or arguments.rollback) and not arguments.data_dir:
        parser.error("恢复时必须指定 --data-dir")
    if not arguments.rollback and not arguments.backup:
        parser.error("必须选择备份文件")
    try:
        result = (
            rollback_restore(arguments.data_dir)
            if arguments.rollback
            else restore_backup(arguments.backup.resolve(), arguments.data_dir)
            if arguments.apply
            else validate_backup(arguments.backup.resolve())
        )
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
