"""以内容哈希保存实际修改，旧轮次的差异不随后续编辑变化。"""

import difflib
import re

from app.core.identifiers import now_iso
from app.infrastructure.storage.files import digest, safe_path
from app.modules.code_work.files import atomic_bytes
from app.modules.source_analysis.workspace import decode_source


def blob(folder, data):
    if data is None:
        return ""
    version = digest(data)
    path = folder / "history" / "blobs" / version
    if not path.exists():
        atomic_bytes(path, data)
    return version


def content(folder, version):
    if not version:
        return None
    if not re.fullmatch(r"[a-f0-9]{64}", version):
        raise ValueError("历史文件版本无效")
    data = safe_path(folder, "history/blobs/" + version).read_bytes()
    if digest(data) != version:
        raise ValueError("历史文件内容校验失败")
    return data


def record(folder, state, path, before, after, *, run_id="", action="edit"):
    previous, current = blob(folder, before), blob(folder, after)
    if previous == current:
        return
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


def difference(path, before, after, *, version=""):
    old, new = decode_source(before or b"")[0], decode_source(after or b"")[0]
    lines = list(
        difflib.unified_diff(
            old.splitlines(), new.splitlines(), "a/" + path, "b/" + path, lineterm=""
        )
    )
    return {
        "path": path,
        "before": old,
        "after": new,
        "diff": "\n".join(lines),
        "version": version or (digest(after) if after is not None else ""),
        "additions": sum(line.startswith("+") for line in lines[2:]),
        "deletions": sum(line.startswith("-") for line in lines[2:]),
    }


def turn_changes(state, run_id):
    result = {}
    for event in state.get("history", []):
        if event["run_id"] != run_id:
            continue
        entry = result.setdefault(event["path"], {"before": event["before"]})
        entry.update(
            after=event["after"], revision=event["revision"], created_at=event["created_at"]
        )
    return {path: entry for path, entry in result.items() if entry["before"] != entry["after"]}


def turn_diff(folder, state, run_id, path):
    changes = turn_changes(state, run_id)
    if path not in changes:
        raise FileNotFoundError("此轮没有修改该文件")
    item = changes[path]
    return {
        **difference(path, content(folder, item["before"]), content(folder, item["after"])),
        "historical": True,
        "run_id": run_id,
    }


def summary(folder, state, run_id):
    changes = turn_changes(state, run_id)
    files = []
    for path, item in sorted(changes.items()):
        diff = turn_diff(folder, state, run_id, path)
        files.append(
            {
                "path": path,
                "kind": "modified" if item["before"] else "added",
                "version": item["after"],
                "additions": diff["additions"],
                "deletions": diff["deletions"],
            }
        )
    return {
        "exists": True,
        "revision": max((item["revision"] for item in changes.values()), default=0),
        "run_id": run_id,
        "scope": "turn",
        "files": files,
        "additions": sum(item["additions"] for item in files),
        "deletions": sum(item["deletions"] for item in files),
    }


def timeline(state):
    turns = {}
    for event in state.get("history", []):
        key = event["run_id"] or f"manual:{event['revision']}"
        entry = turns.setdefault(
            key,
            {
                "id": key,
                "run_id": event["run_id"],
                "started_at": event["created_at"],
                "files": [],
                "action": event["action"],
            },
        )
        entry.update(revision=event["revision"], updated_at=event["created_at"])
        if event["path"] not in entry["files"]:
            entry["files"].append(event["path"])
    return list(reversed(turns.values()))
