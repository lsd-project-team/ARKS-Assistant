"""项目级编码工作区：文件、快照、命令、审批与设置。"""

import hashlib
import json
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from app.core.config import PROJECT_ROOT
from app.core.identifiers import now_iso
from app.modules.coding import files
from app.modules.coding.executor import Executor
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
APPROVAL_TIMEOUT = 300
LOCK_TIMEOUT = 960
OUTPUT_EVENT_CHARS = 1_500
OUTPUT_EVENT_INTERVAL = 0.4


class CodingWorkspace:
    def __init__(self, paths, repository):
        self.root = Path(paths.workspace)
        self.data = Path(paths.data)
        self.project_id = getattr(repository, "project_id", None) or repository.workspace_id
        self.settings_path = self.data / "coding" / "settings" / f"{self.project_id}.json"
        self.audit_path = self.data / "coding" / "audit" / f"{self.project_id}.jsonl"
        self.lock = threading.RLock()
        self.approvals = {}
        self.cancels = {}
        self.snapshots = Snapshots(self.data, self.project_id, self.root)
        self.executor = Executor(
            self.root,
            self.data / "coding" / "logs" / self.project_id,
            self.load_settings()["approval_mode"],
        )

    # ---------- 锁 ----------
    @contextmanager
    def _locked(self):
        if not self.lock.acquire(timeout=LOCK_TIMEOUT):
            raise ValueError("另一个会话正在执行项目命令，请稍后重试")
        try:
            yield
        finally:
            self.lock.release()

    # ---------- 设置 ----------
    def load_settings(self):
        if self.settings_path.exists():
            value = json.loads(self.settings_path.read_text(encoding="utf-8"))
        else:
            value = {}
        return {**DEFAULT_SETTINGS, **value}

    def settings(self):
        return {
            **self.load_settings(),
            "root": str(self.root.resolve()),
            "writable": self.writable(),
            "readonly": self.root.resolve().is_relative_to(READONLY_ROOT),
            "environment": self.environment(),
        }

    def environment(self):
        settings = self.load_settings()
        try:
            detected = files.detect_project(self.root)
        except (OSError, ValueError):
            detected = {}
        return {
            "language": detected.get("language", ""),
            "build_command": settings["build_command"] or detected.get("build", ""),
            "test_command": settings["test_command"] or detected.get("test", ""),
            "detected": detected,
        }

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

    def writable(self):
        """默认分析目录（trunk）及其子目录保持只读，避免问答引用的原代码被就地改写。"""
        root = self.root.resolve()
        return not root.is_relative_to(READONLY_ROOT) or bool(self.load_settings()["enabled"])

    def _require_writable(self):
        if not self.writable():
            raise ValueError("当前是只读分析项目，请选择其他目录建项目，或显式启用该项目的编码")

    # ---------- 文件 ----------
    def list_files(self, path=".", depth=2):
        return files.list_tree(self.root, path, depth)

    def read_file(self, path, start_line=1, end_line=400):
        return files.read_text(self.root, path, start_line, end_line)

    def search_files(self, query, path=".", glob=""):
        return files.search_text(self.root, query, path, glob)

    def find_files(self, pattern, path=".", limit=100):
        return files.find_files(self.root, pattern, path, limit)

    def write_file(self, path, content, expected_hash=""):
        with self._locked():
            self._require_writable()
            self.snapshots.ensure()
            result = files.write_text(self.root, path, content, expected_hash)
            self._touch()
            return result

    def edit_file(self, path, edits, expected_hash=""):
        with self._locked():
            self._require_writable()
            self.snapshots.ensure()
            result = files.edit_text(self.root, path, edits, expected_hash)
            self._touch()
            return result

    def write_binary(self, path, content_base64, expected_hash=""):
        with self._locked():
            self._require_writable()
            self.snapshots.ensure()
            result = files.write_binary(self.root, path, content_base64, expected_hash)
            self._touch()
            return result

    def create_directory(self, path):
        with self._locked():
            self._require_writable()
            self.snapshots.ensure()
            result = files.create_directory(self.root, path)
            self._touch()
            return result

    def move_path(self, path, destination):
        with self._locked():
            self._require_writable()
            self.snapshots.checkpoint("before-move")
            result = files.move(self.root, path, destination)
            self._touch()
            return result

    def delete_path(self, path, recursive=False):
        with self._locked():
            self._require_writable()
            self.snapshots.checkpoint("before-delete")
            result = files.delete(self.root, path, recursive)
            self._touch()
            return result

    # ---------- 快照 ----------
    def begin_run(self, run_id):
        if not self.writable():
            return None
        with self._locked():
            return self.snapshots.checkpoint(f"run-start-{run_id[:8]}")

    def run_changes(self, base, *, limit=400_000):
        with self._locked():
            head = self.snapshots.checkpoint("run-end")
            files_changed = []
            stats = self.snapshots.numstat(base, head)
            for row in self.snapshots.name_status(base, head):
                path = row["path"]
                item = {
                    "path": path,
                    "status": {"A": "added", "D": "deleted", "R": "renamed"}.get(
                        row["status"], "modified"
                    ),
                    **stats.get(path, {"additions": None, "deletions": None, "binary": False}),
                }
                if row.get("previous"):
                    item["previous"] = row["previous"]
                files_changed.append(item)
            diff, truncated = "", False
            for item in files_changed:
                if item["binary"]:
                    continue
                chunk = self.snapshots.diff(base, head, [item["path"]])
                item["patch"] = chunk[:100_000]
                if len(chunk) > 100_000:
                    item["patch"] += "\n…（该文件 diff 过长，已截断）"
                if len(diff) + len(chunk) > limit:
                    diff += "\n…（diff 过长，已截断，请在编码面板查看完整内容）"
                    truncated = True
                    break
                diff += chunk
            return {
                "base": base,
                "head": head,
                "files": files_changed,
                "diff": diff,
                "truncated": truncated,
            }

    def checkpoint(self, label=""):
        with self._locked():
            self._require_writable()
            return {"commit": self.snapshots.checkpoint(label or f"run-{_stamp()}")}

    def checkpoints(self, limit=20):
        if not self.writable():
            return {"checkpoints": [], "changes": [], "readonly": True}
        if not self.snapshots.exists():
            return {
                "checkpoints": [],
                "changes": [],
                "readonly": False,
                "snapshot_unavailable": not self.snapshots.available(),
            }
        return {
            "checkpoints": self.snapshots.log(limit),
            "changes": self.snapshots.status(),
            "readonly": False,
        }

    def diff(self, base="", head="", paths=None, commit=""):
        if not self.snapshots.exists():
            return {"diff": ""}
        if commit:
            return {"diff": self.snapshots.show(commit)}
        return {"diff": self.snapshots.diff(base, head, paths)}

    def restore(self, commit, paths=None):
        with self._locked():
            self._require_writable()
            return self.snapshots.restore(commit, paths)

    def restore_run(self, base, files_changed, commit):
        """撤销某一轮：仅当该轮之后没有新的检查点时允许。"""
        with self._locked():
            self._require_writable()
            if self.snapshots.head() != commit:
                raise ValueError("该轮之后已有新的修改，请先在编码面板中手动回滚")
            self.snapshots.checkpoint("before-undo-run")
            restored = []
            for row in files_changed:
                path = row["path"]
                previous = row.get("previous")
                if previous and self.snapshots.path_in(base, previous):
                    self.snapshots.checkout_paths(base, [previous])
                    target = self.root / path
                    if target.is_file():
                        target.unlink()
                    restored.append(previous)
                    continue
                if self.snapshots.path_in(base, path):
                    self.snapshots.checkout_paths(base, [path])
                    restored.append(path)
                    continue
                target = self.root / path
                if target.is_file():
                    target.unlink()
                    restored.append(path)
                elif target.is_dir():
                    import shutil

                    shutil.rmtree(target, ignore_errors=True)
                    restored.append(path)
            self.snapshots.checkpoint("undo-run")
            return {"commit": base, "paths": restored}

    # ---------- 命令 ----------
    def run_command(
        self,
        command,
        cwd=".",
        timeout=None,
        approved=False,
        *,
        wait=True,
        emit=None,
        run_id="",
        thread_id="",
    ):
        command = (command or "").strip()
        if not command:
            raise ValueError("命令不能为空")
        self._require_writable()
        settings = self.load_settings()
        timeout = max(5, min(int(timeout or settings["timeout_seconds"]), 900))
        approval = None
        if not approved and not self.executor.allowed(command):
            approval = self.request_approval(
                command,
                cwd,
                timeout,
                kind="command",
                emit=emit,
                run_id=run_id,
                thread_id=thread_id,
                waiting=wait,
            )
            if not wait:
                return {"approval_required": True, "approval": _public(approval)}
            status = self._wait_for_approval(approval, run_id)
            if status != "approved":
                result = {
                    "ok": False,
                    "approved": False,
                    "approval_status": status,
                    "command": command,
                    "message": _approval_message(status),
                }
                self._finish_approval(approval, result, status)
                self.cancels.pop(run_id, None)
                return {**result, "approval": self.approval(approval["id"])}
        try:
            result = self._execute_command(command, cwd, timeout, run_id, thread_id, emit)
        except Exception as error:
            if approval is not None:
                self._finish_approval(approval, {"ok": False, "error": str(error)}, "failed")
            raise
        if approval is not None:
            self._finish_approval(approval, result, "approved")
            return {**result, "approval": self.approval(approval["id"])}
        return result

    def _execute_command(self, command, cwd, timeout, run_id, thread_id, emit):
        with self._locked():
            self._require_writable()
            self.snapshots.ensure()
            # 命令可能通过 shell 删除或覆盖文件，执行前先把已有改动存档。
            if self.snapshots.has_changes():
                self.snapshots.checkpoint("before-command")
            stream = self._output_stream(emit, command, run_id)
            cancel = self.cancels.setdefault(run_id, threading.Event()) if run_id else None
            try:
                result = self.executor.run(
                    command,
                    cwd,
                    timeout,
                    approved=True,
                    on_output=stream,
                    cancel=cancel,
                    run_id=run_id,
                )
            finally:
                if stream is not None:
                    stream.flush()
                if run_id:
                    self.cancels.pop(run_id, None)
            self._audit(
                "run",
                command,
                result.get("exit_code"),
                thread_id=thread_id,
                run_id=run_id,
                duration_ms=result.get("duration_ms"),
                output=result.get("output", ""),
            )
            return result

    def start_process(
        self,
        command,
        cwd=".",
        approved=False,
        *,
        wait=True,
        emit=None,
        run_id="",
        thread_id="",
    ):
        command = (command or "").strip()
        if not command:
            raise ValueError("命令不能为空")
        self._require_writable()
        approval = None
        if not approved and not self.executor.allowed(command):
            approval = self.request_approval(
                command,
                cwd,
                120,
                kind="process",
                emit=emit,
                run_id=run_id,
                thread_id=thread_id,
                waiting=wait,
            )
            if not wait:
                return {"approval_required": True, "approval": _public(approval)}
            status = self._wait_for_approval(approval, run_id)
            if status != "approved":
                result = {
                    "ok": False,
                    "approved": False,
                    "approval_status": status,
                    "command": command,
                    "message": _approval_message(status),
                }
                self._finish_approval(approval, result, status)
                self.cancels.pop(run_id, None)
                return {**result, "approval": self.approval(approval["id"])}
        try:
            with self._locked():
                self.snapshots.ensure()
                if self.snapshots.has_changes():
                    self.snapshots.checkpoint("before-process")
                result = self.executor.start(
                    command, cwd, approved=True, run_id=run_id, thread_id=thread_id
                )
                self._audit("start", command, None, thread_id=thread_id, run_id=run_id)
        except Exception as error:
            if approval is not None:
                self._finish_approval(approval, {"ok": False, "error": str(error)}, "failed")
            raise
        if approval is not None:
            self._finish_approval(approval, result, "approved")
            return {**result, "approval": self.approval(approval["id"])}
        return result

    def read_process(self, job_id, lines=80):
        return self.executor.read(job_id, lines)

    def list_jobs(self, limit=30):
        return {"jobs": self.executor.list_jobs(limit)}

    def stop_process(self, job_id):
        return self.executor.stop(job_id)

    def cancel_run(self, run_id):
        event = self.cancels.get(run_id)
        if event is not None:
            event.set()
        self.executor.cancel(run_id)
        with self.lock:
            pending = [
                row
                for row in self.approvals.values()
                if row.get("run_id") == run_id and row["status"] == "pending"
            ]
            for row in pending:
                row["status"] = "cancelled"
        for row in pending:
            self._emit_approval(row)

    def cancel_all(self):
        for run_id in list(self.cancels):
            self.cancel_run(run_id)
        self.executor.stop_all()

    # ---------- 审批 ----------
    def request_approval(
        self,
        command,
        cwd=".",
        timeout=120,
        *,
        kind="command",
        emit=None,
        run_id="",
        thread_id="",
        waiting=False,
    ):
        approval_id = uuid.uuid4().hex[:12]
        row = {
            "id": approval_id,
            "kind": kind,
            "command": command,
            "cwd": cwd,
            "timeout": timeout,
            "status": "pending",
            "created_at": now_iso(),
            "finished_at": None,
            "result": None,
            "run_id": run_id,
            "thread_id": thread_id,
            "_event": threading.Event(),
            "_emit": emit,
            "_waiting": waiting,
        }
        with self.lock:
            self.approvals[approval_id] = row
            if len(self.approvals) > 200:
                finished = sorted(
                    (item for item in self.approvals.values() if item["status"] != "pending"),
                    key=lambda item: item["created_at"],
                )
                for item in finished[: len(self.approvals) - 200]:
                    self.approvals.pop(item["id"], None)
        self._emit_approval(row)
        return row

    def approval(self, approval_id):
        with self.lock:
            row = self.approvals.get(approval_id)
            if not row:
                raise FileNotFoundError("审批请求不存在或已过期")
            return _public(row)

    def list_approvals(self):
        with self.lock:
            return [_public(row) for row in self.approvals.values() if row["status"] == "pending"]

    def recent_approvals(self, limit=20):
        with self.lock:
            rows = sorted(
                self.approvals.values(), key=lambda item: item["created_at"], reverse=True
            )[: max(1, min(limit, 100))]
            return [_public(row) for row in rows]

    def decide_approval(self, approval_id, approved):
        with self.lock:
            row = self.approvals.get(approval_id)
            if not row:
                raise FileNotFoundError("审批请求不存在或已过期")
            if row["status"] != "pending":
                raise ValueError("该请求已经处理")
            row["status"] = "approved" if approved else "rejected"
            waiting = bool(row.get("_waiting"))
            row["_event"].set()
        if waiting:
            # 等待中的工具线程会在收到结果后执行并回填。
            return self.approval(approval_id)
        if not approved:
            self._finish_approval(
                row,
                {"ok": False, "approved": False, "message": "用户拒绝了这条命令"},
                "rejected",
            )
            return self.approval(approval_id)
        result = self._approved_result(row)
        self._finish_approval(row, result, "approved")
        return self.approval(approval_id)

    def _approved_result(self, row):
        try:
            if row["kind"] == "process":
                return self.start_process(
                    row["command"],
                    row["cwd"],
                    approved=True,
                    wait=False,
                    emit=row.get("_emit"),
                    run_id=row.get("run_id", ""),
                    thread_id=row.get("thread_id", ""),
                )
            return self.run_command(
                row["command"],
                row["cwd"],
                row["timeout"],
                approved=True,
                wait=False,
                emit=row.get("_emit"),
                run_id=row.get("run_id", ""),
                thread_id=row.get("thread_id", ""),
            )
        except Exception as error:  # 审批执行失败要回到界面，而不是静默丢失
            return {"ok": False, "error": str(error)}

    def _wait_for_approval(self, approval, run_id):
        deadline = time.monotonic() + APPROVAL_TIMEOUT
        cancel = self.cancels.setdefault(run_id, threading.Event()) if run_id else None
        while True:
            with self.lock:
                row = self.approvals.get(approval["id"], {})
                if row.get("status") != "pending":
                    return row.get("status", "expired")
            if cancel is not None and cancel.is_set():
                with self.lock:
                    row = self.approvals.get(approval["id"])
                    if row and row["status"] == "pending":
                        row["status"] = "cancelled"
                return "cancelled"
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                with self.lock:
                    row = self.approvals.get(approval["id"])
                    if row and row["status"] == "pending":
                        row["status"] = "expired"
                return "expired"
            with self.lock:
                row = self.approvals.get(approval["id"])
                event = row["_event"] if row else None
            if event is not None:
                event.wait(min(0.5, remaining))
            else:
                return "expired"

    def _finish_approval(self, row, result, status):
        with self.lock:
            row["result"] = result
            row["status"] = status
            row["finished_at"] = now_iso()
        self._emit_approval(row)

    def _emit_approval(self, row):
        emit = row.get("_emit")
        if emit is None:
            return
        try:
            emit("coding_approval", _public(row))
        except Exception:
            pass

    def _output_stream(self, emit, command, run_id):
        if emit is None:
            return None
        state = {"buffer": [], "last": 0.0}

        def flush(force=False):
            text = "".join(state["buffer"])
            if not text:
                return
            now = time.monotonic()
            pending = len(text) < OUTPUT_EVENT_CHARS
            if not force and pending and now - state["last"] < OUTPUT_EVENT_INTERVAL:
                return
            state["buffer"] = []
            state["last"] = now
            try:
                emit(
                    "coding_output",
                    {
                        "command": command,
                        "chunk": text[-8_000:],
                        "run_id": run_id,
                        "truncated": len(text) > 8_000,
                    },
                )
            except Exception:
                pass

        def receive(text):
            state["buffer"].append(text)
            flush()

        receive.flush = lambda: flush(True)
        return receive

    # ---------- 审计 ----------
    def list_audit(self, limit=50):
        if not self.audit_path.exists():
            return []
        rows = []
        for line in self.audit_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        return rows[::-1][: max(1, min(limit, 500))]

    # ---------- 辅助 ----------
    def _touch(self):
        stamps = self.data / "coding" / "activity"
        stamps.mkdir(parents=True, exist_ok=True)
        (stamps / f"{self.project_id}.json").write_text(
            json.dumps({"updated_at": now_iso(), "root": str(self.root)}), encoding="utf-8"
        )

    def _audit(
        self,
        action,
        command,
        exit_code,
        *,
        thread_id="",
        run_id="",
        duration_ms=None,
        output="",
    ):
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "at": now_iso(),
            "project": self.project_id,
            "action": action,
            "command": command,
            "exit_code": exit_code,
            "mode": self.load_settings()["approval_mode"],
            "thread_id": thread_id,
            "run_id": run_id,
            "duration_ms": duration_ms,
            "output_digest": hashlib.sha256(output.encode("utf-8")).hexdigest() if output else "",
        }
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def _public(row):
    return {key: value for key, value in row.items() if not key.startswith("_")}


def _approval_message(status):
    if status == "rejected":
        return "用户拒绝了这条命令，不要重试；需要时先说明原因再询问。"
    if status == "cancelled":
        return "本轮已被用户停止，命令没有执行。"
    return "等待用户确认超时，命令没有执行；请说明需要确认的命令，不要反复重试。"


def _stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")
