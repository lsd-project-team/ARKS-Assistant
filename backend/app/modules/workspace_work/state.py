"""对话内的修改日志与快照；内容按哈希寻址，旧轮次不随后续编辑漂移。"""

import json
import re
from pathlib import Path

from app.core.identifiers import now_iso
from app.infrastructure.storage.files import digest, safe_path
from app.modules.workspace_work.paths import atomic_bytes


class Journal:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.state_file = self.folder / "state.json"
        self.blob_root = self.folder / "blobs"

    def exists(self):
        return self.state_file.is_file()

    def load(self):
        if not self.state_file.is_file():
            return None
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def save(self, state):
        atomic_bytes(
            self.state_file,
            json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8"),
        )

    def blob(self, data):
        if data is None:
            return ""
        version = digest(data)
        path = self.blob_root / version
        if not path.is_file():
            atomic_bytes(path, data)
        return version

    def content(self, version):
        if not version:
            return None
        if not re.fullmatch(r"[a-f0-9]{64}", version):
            raise ValueError("快照标识无效")
        path = safe_path(self.folder, "blobs/" + version)
        if not path.is_file():
            raise FileNotFoundError("快照内容不存在")
        data = path.read_bytes()
        if digest(data) != version:
            raise ValueError("快照内容校验失败")
        return data


def new_state(thread_id, root):
    return {
        "thread_id": thread_id,
        "root": str(root),
        "created_at": now_iso(),
        "revision": 0,
        "files": {},
        "history": [],
        "commands": [],
        "approvals": [],
    }


def record(journal, state, path, before, after, *, action="edit", run_id="", track=True):
    previous, current = journal.blob(before), journal.blob(after)
    if previous == current:
        return None
    state["revision"] += 1
    event = {
        "revision": state["revision"],
        "run_id": run_id or "",
        "action": action,
        "path": path,
        "before": previous,
        "after": current,
        "created_at": now_iso(),
    }
    state.setdefault("history", []).append(event)
    if not track:
        return event
    existing = state.setdefault("files", {}).get(path)
    first = existing["before"] if existing else previous
    kind = "added" if not first else "modified"
    state["files"][path] = {"kind": kind, "before": first, "after": current}
    return event
