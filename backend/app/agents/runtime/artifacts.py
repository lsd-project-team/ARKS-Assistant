"""聊天工具只能访问本对话的临时产物，不能横跨项目读取隔离副本。"""

import os
from hashlib import sha256
from pathlib import Path
from threading import RLock

from app.modules.code_changes.files import digest, inventory, safe_path

_migration_lock = RLock()


def thread_artifacts(scratch, thread_id):
    if os.name == "nt" and not str(scratch).startswith("\\\\?\\"):
        # 原生文件工具使用 os.open；深目录的会话归档需要 Win32 长路径前缀。
        value = str(scratch.resolve())
        scratch = Path(
            "\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value
        )
    identity = sha256(thread_id.encode()).hexdigest()[:24]
    with _migration_lock:
        root = safe_path(scratch, f"agent-work/{identity}")
        root.mkdir(parents=True, exist_ok=True)
        marker = safe_path(root, "legacy-migrated")
        if marker.exists():
            return root
        # 只迁移已经通过对话权限检查的当前会话旧产物，保留原虚拟路径供检查点引用。
        legacy = safe_path(scratch, f"threads/{thread_id}")
        if legacy.is_dir():
            manifest = inventory(legacy)
            target = safe_path(root, f"threads/{thread_id}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.mkdir(exist_ok=True)
            for relative, version in manifest.items():
                data = safe_path(legacy, relative).read_bytes()
                if digest(data) != version:
                    raise ValueError("旧会话产物在迁移期间发生变化，请重试")
                destination = safe_path(target, relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    destination.write_bytes(data)
        marker.write_text("1", encoding="utf-8")
        return root
