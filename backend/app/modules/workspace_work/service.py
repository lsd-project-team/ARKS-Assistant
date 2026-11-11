"""对话级工作区：直接读写已配置目录，逐次快照，命令需白名单与审批。"""

import uuid
from pathlib import Path
from threading import Event, RLock

from app.core.identifiers import now_iso
from app.infrastructure.storage.files import digest
from app.modules.workspace_work import commands, diff, paths
from app.modules.workspace_work.environment import WorkspaceEnvironment
from app.modules.workspace_work.state import Journal, new_state, record

_lock = RLock()
_events = {}
MAX_STATUS_FILES = 200
MAX_STORED_OUTPUT = 20_000


class WorkspaceWork:
    def __init__(self, paths_obj, repository):
        self.paths, self.repository = paths_obj, repository
        self.environment = WorkspaceEnvironment(paths_obj.data)

    # ---------- 目录与状态 ----------

    def project(self):
        return self.repository.project_id or "independent"

    def folder(self, thread_id):
        self.repository.catalog.get(thread_id)
        parent = self.paths.scratch / "ww"
        parent.mkdir(parents=True, exist_ok=True)
        return parent / digest(thread_id.encode())[:12]

    def _journal(self, thread_id):
        folder = self.folder(thread_id)
        folder.mkdir(parents=True, exist_ok=True)
        return Journal(folder)

    def _root(self, thread_id, state=None):
        configured = self.environment.load(self.project())
        if not configured.root:
            raise ValueError("请先由管理员配置本项目的代码工作目录")
        root = paths.workspace_root(configured.root)
        if state and state.get("root") and Path(state["root"]) != root:
            raise ValueError("工作目录已变更，请在新对话中继续")
        return root

    def _state(self, thread_id):
        journal = self._journal(thread_id)
        state = journal.load()
        if not state:
            root = self._root(thread_id)
            state = new_state(thread_id, root)
            journal.save(state)
        elif state.get("thread_id") != thread_id:
            raise ValueError("工作区状态标识冲突，请使用新对话")
        return journal, state

    def status(self, thread_id):
        with _lock:
            configured = self.environment.load(self.project())
            if not configured.root:
                return {"exists": False, "configured": False, "root": ""}
            root = paths.workspace_root(configured.root)
            folder = self.folder(thread_id)
            journal = Journal(folder)
            state = journal.load()
            if not state:
                return {
                    "exists": True,
                    "configured": True,
                    "root": str(root),
                    "revision": 0,
                    "files": [],
                    "file_count": 0,
                    "additions": 0,
                    "deletions": 0,
                    "approvals": [],
                    "commands": [],
                }
            rows = []
            for path, item in sorted(state.get("files", {}).items()):
                before = journal.content(item["before"])
                current_path, _ = paths.resolve(state["root"], path)
                after = paths.read_bytes(current_path) if current_path.is_file() else None
                if after is None:
                    continue
                result = diff.difference(path, before or b"", after)
                rows.append(
                    {
                        "path": path,
                        "kind": item["kind"],
                        "version": digest(after),
                        "additions": result["additions"],
                        "deletions": result["deletions"],
                    }
                )
            return {
                "exists": True,
                "configured": True,
                "root": state["root"],
                "revision": state["revision"],
                "files": rows[:MAX_STATUS_FILES],
                "file_count": len(rows),
                "additions": sum(row["additions"] for row in rows),
                "deletions": sum(row["deletions"] for row in rows),
                "approvals": [
                    row for row in state.get("approvals", []) if row["status"] == "pending"
                ],
                "commands": state.get("commands", [])[-10:],
            }

    # ---------- 文件读写 ----------

    def list(self, thread_id, path=""):
        with _lock:
            _, state = self._state(thread_id)
            root = Path(state["root"])
            target, relative = paths.resolve(root, path) if path else (root, "")
            if not target.is_dir():
                raise ValueError("目录不存在")
            entries = []
            for child in sorted(target.iterdir(), key=lambda item: (item.is_file(), item.name)):
                if child.name in paths.IGNORED or child.is_symlink():
                    continue
                entries.append(
                    {
                        "name": child.name,
                        "path": (relative + "/" + child.name).strip("/"),
                        "type": "file" if child.is_file() else "directory",
                        "size": child.stat().st_size if child.is_file() else 0,
                    }
                )
                if len(entries) >= 500:
                    break
            return {"path": relative, "entries": entries}

    def read(self, thread_id, path, start_line=1, end_line=400):
        with _lock:
            _, state = self._state(thread_id)
            target, relative = paths.resolve(state["root"], path)
            if not relative:
                raise ValueError("请提供文件路径")
            data = paths.read_bytes(target)
            text = paths.text_of(data)
            lines = text.splitlines()
            if start_line < 1 or end_line < start_line or end_line - start_line >= 2_000:
                raise ValueError("每次读取 1–2000 行，行号从 1 开始")
            chunk = "\n".join(
                f"{index}: {line}"
                for index, line in enumerate(lines, 1)
                if start_line <= index <= end_line
            )
            return {
                "path": relative,
                "version": digest(data),
                "start_line": start_line,
                "end_line": min(end_line, len(lines)),
                "line_count": len(lines),
                "content": chunk,
            }

    def write(self, thread_id, path, content, version, *, run_id="", action="write"):
        with _lock:
            journal, state = self._state(thread_id)
            target, relative = paths.resolve(state["root"], path)
            if not relative:
                raise ValueError("请提供文件路径")
            if target.exists() and not target.is_file():
                raise ValueError("目标路径是目录，不能写入")
            existed = target.is_file()
            current = target.read_bytes() if existed else b""
            if version != (digest(current) if existed else ""):
                raise ValueError("文件已更新，请重新读取当前版本后修改")
            updated = paths.encode(content, current)
            if existed and updated == current:
                return {"path": relative, "version": digest(current), "changed": False}
            paths.atomic_bytes(target, updated)
            try:
                record(
                    journal,
                    state,
                    relative,
                    current if existed else None,
                    updated,
                    action=action,
                    run_id=run_id,
                )
                journal.save(state)
            except OSError:
                if existed:
                    paths.atomic_bytes(target, current)
                else:
                    target.unlink(missing_ok=True)
                raise
            return {
                "path": relative,
                "version": digest(updated),
                "changed": True,
                "revision": state["revision"],
            }

    def edit(self, thread_id, path, old_text, new_text, version, *, run_id=""):
        with _lock:
            journal, state = self._state(thread_id)
            target, relative = paths.resolve(state["root"], path)
            data = paths.read_bytes(target)
            if digest(data) != version:
                raise ValueError("文件已更新，请重新读取当前版本后修改")
            text = paths.text_of(data).replace("\r\n", "\n")
            old = (old_text or "").replace("\r\n", "\n")
            if not old or text.count(old) != 1:
                raise ValueError("待替换原文必须在文件中唯一匹配；请扩大上下文后重试")
            content = text.replace(old, (new_text or "").replace("\r\n", "\n"), 1)
            return self.write(thread_id, relative, content, version, run_id=run_id, action="edit")

    def apply_patch(self, thread_id, edits, *, run_id=""):
        """多文件原子编辑：先全部校验，再写盘；任一失败回滚已写文件。"""
        if not edits or len(edits) > 50:
            raise ValueError("每次补丁需要 1–50 个文件修改")
        with _lock:
            journal, state = self._state(thread_id)
            root = Path(state["root"])
            planned = []
            seen = set()
            for item in edits:
                path = item.get("path", "")
                if path in seen:
                    raise ValueError("同一补丁不能重复修改同一文件：" + path)
                seen.add(path)
                target, relative = paths.resolve(root, path)
                if not relative:
                    raise ValueError("请提供文件路径")
                if target.exists() and not target.is_file():
                    raise ValueError("目标路径是目录，不能写入")
                existed = target.is_file()
                current = target.read_bytes() if existed else b""
                expected = item.get("version", "")
                if expected != (digest(current) if existed else ""):
                    raise ValueError("文件已更新，请重新读取当前版本后修改：" + relative)
                text = paths.text_of(current).replace("\r\n", "\n") if existed else ""
                old = (item.get("old_text") or "").replace("\r\n", "\n")
                if old:
                    if text.count(old) != 1:
                        raise ValueError("待替换原文必须在文件中唯一匹配：" + relative)
                    text = text.replace(old, (item.get("new_text") or "").replace("\r\n", "\n"), 1)
                else:
                    text = item.get("new_text") or ""
                planned.append(
                    (target, relative, current if existed else None, paths.encode(text, current))
                )
            written = []
            try:
                for target, relative, before, updated in planned:
                    if before is not None and updated == before:
                        continue
                    paths.atomic_bytes(target, updated)
                    written.append((target, relative, before))
                    record(journal, state, relative, before, updated, action="patch", run_id=run_id)
                journal.save(state)
            except OSError:
                for target, _, before in reversed(written):
                    if before is None:
                        target.unlink(missing_ok=True)
                    else:
                        paths.atomic_bytes(target, before)
                raise
            return {
                "revision": state["revision"],
                "files": [
                    {"path": relative, "version": digest(updated), "changed": updated != before}
                    for _, relative, before, updated in planned
                ],
            }

    def search(self, thread_id, query, limit=60):
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise ValueError("搜索词长度必须在 1–200 之间")
        with _lock:
            _, state = self._state(thread_id)
            root = Path(state["root"])
        needle = query.strip().lower()
        results = []
        for file in paths.walk(root, limit=paths.MAX_SEARCH_FILES):
            if len(results) >= limit:
                break
            try:
                data = paths.read_bytes(file)
                text = paths.text_of(data)
            except (OSError, ValueError):
                continue
            for index, line in enumerate(text.splitlines(), 1):
                if needle in line.lower():
                    results.append(
                        {
                            "path": file.relative_to(root).as_posix(),
                            "line": index,
                            "text": line.strip()[:200],
                        }
                    )
                    if len(results) >= limit:
                        break
        return {"query": query, "matches": results[:limit], "limited": len(results) >= limit}

    # ---------- 差异、快照与还原 ----------

    def diff(self, thread_id, path, run_id=""):
        with _lock:
            journal, state = self._state(thread_id)
            if path not in state.get("files", {}):
                raise FileNotFoundError("此文件没有本对话的修改记录")
            entry = state["files"][path]
            if run_id:
                events = [row for row in state.get("history", []) if row["run_id"] == run_id]
                changes = [row for row in events if row["path"] == path]
                if not changes:
                    raise FileNotFoundError("此轮没有修改该文件")
                before = journal.content(changes[0]["before"])
                after = journal.content(changes[-1]["after"])
                return {
                    **diff.difference(path, before or b"", after or b""),
                    "historical": True,
                    "run_id": run_id,
                }
            target, _ = paths.resolve(state["root"], path)
            after = paths.read_bytes(target) if target.is_file() else None
            before = journal.content(entry["before"])
            return diff.difference(path, before or b"", after or b"")

    def restore(self, thread_id, path="", revision=None):
        with _lock:
            journal, state = self._state(thread_id)
            root = Path(state["root"])
            targets = [path] if path else sorted(state.get("files", {}))
            if not targets:
                raise ValueError("当前对话没有可还原的修改")
            for relative in targets:
                entry = state.get("files", {}).get(relative)
                if not entry:
                    raise ValueError("此文件没有本对话的修改记录：" + relative)
                target, _ = paths.resolve(root, relative)
                before = journal.content(entry["before"])
                current = target.read_bytes() if target.is_file() else None
                if current == before:
                    state["files"].pop(relative, None)
                    continue
                if before is None:
                    target.unlink(missing_ok=True)
                else:
                    paths.atomic_bytes(target, before)
                record(
                    journal,
                    state,
                    relative,
                    current,
                    before,
                    action="restore",
                    track=False,
                )
                state["files"].pop(relative, None)
            journal.save(state)
            return self.status(thread_id)

    # ---------- 命令与审批 ----------

    def run_command(self, thread_id, argv, cwd="", timeout=None, run_id=""):
        config = self.environment.load(self.project())
        rule = commands.matched_rule(argv, config.commands)
        if not rule:
            raise commands.CommandDenied(
                "命令不在白名单内：" + " ".join(argv[:3]) + "；请由管理员在配置中添加"
            )
        with _lock:
            journal, state = self._state(thread_id)
            root = Path(state["root"])
            if cwd in ("", ".", "./"):
                workdir, relative = root, ""
            else:
                workdir, relative = paths.resolve(root, cwd)
            if not workdir.is_dir():
                raise ValueError("命令工作目录不存在")
            limit = min(timeout or config.command_timeout_seconds, config.command_timeout_seconds)
            command = {
                "id": uuid.uuid4().hex,
                "argv": argv,
                "cwd": relative,
                "run_id": run_id,
                "status": "pending",
                "created_at": now_iso(),
            }
            approval = None
            event = None
            if not config.auto_approve:
                approval = {
                    "id": uuid.uuid4().hex,
                    "command": command["id"],
                    "argv": argv,
                    "cwd": relative,
                    "status": "pending",
                    "created_at": now_iso(),
                }
                state.setdefault("approvals", []).append(approval)
                state.setdefault("commands", []).append(command)
                journal.save(state)
                event = Event()
                _events[approval["id"]] = event
        if event is not None:
            event.wait(config.approval_timeout_seconds)
            with _lock:
                journal, state = self._state(thread_id)
                current = next(
                    (row for row in state.get("approvals", []) if row["id"] == approval["id"]),
                    None,
                )
                _events.pop(approval["id"], None)
                if not current or current["status"] != "approved":
                    status = "denied" if current and current["status"] == "denied" else "timeout"
                    command = next(
                        (row for row in state.get("commands", []) if row["id"] == command["id"]),
                        command,
                    )
                    command.update(status=status, finished_at=now_iso())
                    journal.save(state)
                    return {
                        "command_id": command["id"],
                        "status": status,
                        "output": "命令未获批准，未执行。"
                        if status == "denied"
                        else "等待批准超时，未执行。",
                    }
        return self._execute(thread_id, command["id"], argv, workdir, relative, limit)

    def _execute(self, thread_id, command_id, argv, workdir, relative, timeout):
        started = now_iso()
        try:
            result = commands.run(argv, workdir, timeout)
            status = (
                "timeout"
                if result["timed_out"]
                else ("passed" if result["exit_code"] == 0 else "failed")
            )
            output = result["output"]
        except Exception as error:  # 执行前错误也要落在同一份记录里
            result, status, output = {"exit_code": None}, "failed", str(error)
        with _lock:
            journal, state = self._state(thread_id)
            rows = state.setdefault("commands", [])
            row = next((item for item in rows if item["id"] == command_id), None)
            value = {
                "id": command_id,
                "argv": argv,
                "cwd": relative,
                "status": status,
                "exit_code": result.get("exit_code"),
                "output": output[-MAX_STORED_OUTPUT:],
                "started_at": started,
                "finished_at": now_iso(),
                "truncated": bool(result.get("truncated")),
            }
            if row:
                row.update(value)
            else:
                rows.append(value)
            journal.save(state)
        return {"command_id": command_id, "status": status, **result, "output": output}

    def decide_approval(self, thread_id, approval_id, decision, actor):
        if decision not in {"approve", "deny"}:
            raise ValueError("审批结果只能是 approve 或 deny")
        with _lock:
            journal, state = self._state(thread_id)
            row = next(
                (item for item in state.get("approvals", []) if item["id"] == approval_id), None
            )
            if not row:
                raise FileNotFoundError("审批请求不存在")
            if row["status"] != "pending":
                raise ValueError("该审批已处理")
            row.update(
                status="approved" if decision == "approve" else "denied",
                decided_at=now_iso(),
                decided_by=actor,
            )
            journal.save(state)
            event = _events.get(approval_id)
            if event:
                event.set()
            return {"id": approval_id, "status": row["status"]}
