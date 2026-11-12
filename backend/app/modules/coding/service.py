"""项目级编码工作区：文件、快照、命令与设置。"""

import json
from datetime import datetime
from pathlib import Path
from threading import RLock

from app.core.config import PROJECT_ROOT
from app.core.identifiers import now_iso
from app.modules.coding import files
from app.modules.coding.executor import ApprovalRequired, Executor
from app.modules.coding.snapshots import Snapshots

DEFAULT_SETTINGS = {
    "approval_mode": "allowlist",
    "timeout_seconds": 120,
    "build_command": "",
    "test_command": "",
    "enabled": False,
}
MODES = {"allowlist", "confirm", "full"}
READONLY_ROOT = (PROJECT_ROOT / "trunk").resolve()


class CodingWorkspace:
    def __init__(self, paths, repository):
        self.root = Path(paths.workspace)
        self.data = Path(paths.data)
        self.project_id = getattr(repository, "project_id", None) or repository.workspace_id
        self.settings_path = self.data / "coding" / "settings" / f"{self.project_id}.json"
        self.audit_path = self.data / "coding" / "audit" / f"{self.project_id}.jsonl"
        self.lock = RLock()
        self.snapshots = Snapshots(self.data, self.project_id, self.root)
        self.executor = Executor(
            self.root,
            self.data / "coding" / "logs" / self.project_id,
            self.load_settings()["approval_mode"],
        )

    # ---------- 设置 ----------
    def load_settings(self):
        if self.settings_path.exists():
            value = json.loads(self.settings_path.read_text(encoding="utf-8"))
        else:
            value = {}
        return {**DEFAULT_SETTINGS, **value}

    def settings(self):
        return {**self.load_settings(), "root": str(self.root.resolve())}

    def save_settings(self, changes):
        value = self.load_settings()
        if "approval_mode" in changes:
            if changes["approval_mode"] not in MODES:
                raise ValueError("审批档位必须是 allowlist / confirm / full")
            value["approval_mode"] = changes["approval_mode"]
        if "timeout_seconds" in changes:
            timeout = int(changes["timeout_seconds"])
            if not 10 <= timeout <= 900:
                raise ValueError("超时必须在 10~900 秒")
            value["timeout_seconds"] = timeout
        for key in ("build_command", "test_command"):
            if key in changes:
                value[key] = str(changes[key])[:500]
        if "enabled" in changes:
            value["enabled"] = bool(changes["enabled"])
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.executor.mode = value["approval_mode"]
        return self.settings()

    # ---------- 文件 ----------
    def list_files(self, path=".", depth=2):
        return files.list_tree(self.root, path, depth)

    def read_file(self, path, start_line=1, end_line=400):
        return files.read_text(self.root, path, start_line, end_line)

    def search_files(self, query, path=".", glob=""):
        return files.search_text(self.root, query, path, glob)

    def _guard_write(self):
        """默认分析目录（trunk）保持只读，避免问答引用的原代码被就地改写。"""
        if self.root.resolve() == READONLY_ROOT and not self.load_settings()["enabled"]:
            raise ValueError("当前是只读分析项目，请选择其他目录建项目，或显式启用该项目的编码")

    def write_file(self, path, content, expected_hash=""):
        with self.lock:
            self._guard_write()
            self.snapshots.ensure()
            result = files.write_text(self.root, path, content, expected_hash)
            self._touch()
            return result

    def create_directory(self, path):
        with self.lock:
            self._guard_write()
            self.snapshots.ensure()
            result = files.create_directory(self.root, path)
            self._touch()
            return result

    def move_path(self, path, destination):
        with self.lock:
            self._guard_write()
            self.snapshots.checkpoint("before-move")
            result = files.move(self.root, path, destination)
            self._touch()
            return result

    def delete_path(self, path, recursive=False):
        with self.lock:
            self._guard_write()
            self.snapshots.checkpoint("before-delete")
            result = files.delete(self.root, path, recursive)
            self._touch()
            return result

    # ---------- 快照 ----------
    def checkpoint(self, label=""):
        with self.lock:
            return {"commit": self.snapshots.checkpoint(label or f"run-{_stamp()}")}

    def checkpoints(self, limit=20):
        return {"checkpoints": self.snapshots.log(limit), "changes": self.snapshots.status()}

    def diff(self, base="", head="", paths=None):
        return {"diff": self.snapshots.diff(base, head, paths)}

    def restore(self, commit, paths=None):
        with self.lock:
            return self.snapshots.restore(commit, paths)

    # ---------- 命令 ----------
    def run_command(self, command, cwd=".", timeout=None, approved=False):
        with self.lock:
            self._guard_write()
            settings = self.load_settings()
            try:
                result = self.executor.run(
                    command,
                    cwd,
                    timeout or settings["timeout_seconds"],
                    approved=approved,
                )
            except ApprovalRequired:
                raise
            self._audit("run", command, result.get("exit_code"))
            return result

    def start_process(self, command, cwd=".", approved=False):
        self._guard_write()
        result = self.executor.start(command, cwd, approved=approved)
        self._audit("start", command, None)
        return result

    def read_process(self, job_id, lines=80):
        return self.executor.read(job_id, lines)

    def stop_process(self, job_id):
        return self.executor.stop(job_id)

    # ---------- 辅助 ----------
    def _touch(self):
        stamps = self.data / "coding" / "activity"
        stamps.mkdir(parents=True, exist_ok=True)
        (stamps / f"{self.project_id}.json").write_text(
            json.dumps({"updated_at": now_iso(), "root": str(self.root)}), encoding="utf-8"
        )

    def _audit(self, action, command, exit_code):
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "at": now_iso(),
            "project": self.project_id,
            "action": action,
            "command": command,
            "exit_code": exit_code,
            "mode": self.load_settings()["approval_mode"],
        }
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def _stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")
