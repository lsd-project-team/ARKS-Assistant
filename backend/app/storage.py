"""存储占用仅统计文件大小和记录数量，不读取密钥内容。"""

import shutil

from app.backup_manifest import database_info


def storage_stats(paths) -> dict:
    groups = dict.fromkeys(("databases", "memories", "archives", "backups", "recovery", "other"), 0)
    unreadable = 0
    for file in paths.data.rglob("*"):
        try:
            if (
                not file.is_file()
                or file.is_symlink()
                or not file.resolve().is_relative_to(paths.data)
            ):
                continue
            first = file.relative_to(paths.data).parts[0]
            group = (
                "databases"
                if first.startswith(("app.sqlite3", "checkpoints.sqlite3"))
                else "memories"
                if first == "memories"
                else "archives"
                if first == "scratch"
                else "backups"
                if first == "backups"
                else "recovery"
                if first.startswith(".restore-recovery-")
                else "other"
            )
            groups[group] += file.stat().st_size
        except OSError:
            unreadable += 1
    disk = shutil.disk_usage(paths.data)
    return {
        "groups": groups,
        "total_bytes": sum(groups.values()),
        "disk_free_bytes": disk.free,
        "unreadable_files": unreadable,
        **database_info(paths.data / "app.sqlite3", business=True, verify=False, immutable=False),
    }
