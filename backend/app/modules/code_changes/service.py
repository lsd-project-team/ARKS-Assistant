"""隔离副本、乐观补丁和绑定版本的命令验证。"""

import asyncio
import json
import shutil
import threading
from pathlib import Path

from sqlalchemy import select

from app.core.identifiers import new_id, now_iso
from app.modules.code_changes.files import (
    changes_diff,
    copy_snapshot,
    digest,
    edit_text,
    export_patch,
    inventory,
    read_text,
    remove_copy,
    safe_path,
    tree_version,
)
from app.modules.code_changes.models import (
    CodeChangeRecord,
    VerificationProfileRecord,
    VerificationRecord,
)
from app.modules.code_changes.processes import VerificationTask, run_process
from app.modules.code_changes.schemas import ChangeWrite, ProfileWrite

OUTPUT_BYTES = 64_000


class CodeChanges:
    def __init__(self, paths, database, workspace, project_id):
        self.paths, self.database, self.workspace = paths, database, workspace
        self._project_id = project_id
        self.storage = paths.scratch / "code-changes"
        self._lock = threading.RLock()
        self.lock = self._lock
        self._tasks = {}
        self._closed = False

    @property
    def project_id(self):
        value = self._project_id() if callable(self._project_id) else self._project_id
        if not value:
            raise ValueError("代码修改缺少项目身份")
        return str(value)

    def bind_project(self, project_id):
        self._project_id = project_id

    def _scope(self, project_id):
        if self.storage.resolve().is_relative_to(self.workspace.root.resolve()):
            raise ValueError("隔离副本必须放在源码目录之外")
        self.storage.mkdir(parents=True, exist_ok=True)
        scope = digest(project_id.encode())
        folder = safe_path(self.storage, scope)
        folder.mkdir(exist_ok=True)
        return folder

    def _folder(self, row):
        return safe_path(self._scope(row.project_id), row.id)

    def _work(self, row):
        folder = self._folder(row)
        return safe_path(folder, "work")

    def _row(self, session, identifier, project_id=None):
        row = session.scalar(
            select(CodeChangeRecord).where(
                CodeChangeRecord.id == identifier,
                CodeChangeRecord.project_id == (project_id or self.project_id),
            )
        )
        if row is None:
            raise FileNotFoundError("隔离修改不存在")
        return row

    @staticmethod
    def _editable(row):
        if row.status in {"discarded", "verifying"}:
            raise ValueError("验证中或已丢弃的副本不能修改")

    def create(self, title, goal):
        body = ChangeWrite(title=title, goal=goal)
        if getattr(self.workspace, "attached", {}):
            raise ValueError("隔离修改暂不支持附加源码目录，请使用只关联主目录的项目")
        if self.storage.resolve().is_relative_to(self.workspace.root.resolve()):
            raise ValueError("隔离副本必须放在源码目录之外，请调整项目源码目录")
        project_id = self.project_id
        with self._lock:
            row = CodeChangeRecord(
                id=new_id(),
                project_id=project_id,
                title=body.title,
                goal=body.goal,
                status="ready",
                source_root=str(self.workspace.root.resolve()),
            )
            folder = self._folder(row)
            folder.mkdir()
            try:
                manifest = copy_snapshot(Path(row.source_root), folder / "base", folder / "work")
                row.manifest_json = json.dumps(manifest)
                row.change_version = tree_version(manifest)
                with self.database.session.begin() as session:
                    session.add(row)
                return self.get(row.id)
            except BaseException:
                if folder.exists():
                    remove_copy(self._scope(project_id), folder)
                raise

    def list(self):
        with self._lock, self.database.session.begin() as session:
            rows = session.scalars(
                select(CodeChangeRecord)
                .where(
                    CodeChangeRecord.project_id == self.project_id,
                )
                .order_by(CodeChangeRecord.created_at.desc())
            )
            result = []
            for row in rows:
                if row.status == "passed":
                    self._refresh(row)
                result.append(self._serialize(session, row))
            return result

    def get(self, identifier):
        with self._lock, self.database.session.begin() as session:
            row = self._row(session, identifier)
            if row.status == "passed":
                self._refresh(row)
            return self._serialize(session, row)

    def _refresh(self, row):
        current, files, _ = changes_diff(
            safe_path(self._folder(row), "base"),
            self._work(row),
            json.loads(row.manifest_json),
        )
        version = tree_version(current)
        if version != row.change_version:
            row.status = "editing"
            row.change_version = version
            row.error = "副本已改变，需要重新验证"
            row.updated_at = now_iso()
        row.files_changed = len(files)
        return version

    @staticmethod
    def _source_conflicts(row):
        baseline = json.loads(row.manifest_json)
        source = inventory(Path(row.source_root))
        return [
            path
            for path in sorted(set(source) | set(baseline))
            if source.get(path) != baseline.get(path)
        ]

    def read_file(self, identifier, path):
        with self._lock, self.database.session() as session:
            row = self._row(session, identifier)
            if row.status == "discarded":
                raise ValueError("副本已丢弃")
            return read_text(self._work(row), path)

    def edit_file(self, identifier, path, before, after, version):
        with self._lock, self.database.session.begin() as session:
            row = self._row(session, identifier)
            self._editable(row)
            original = safe_path(Path(row.source_root), path)
            path = original.relative_to(Path(row.source_root)).as_posix()
            baseline = json.loads(row.manifest_json)
            original_version = digest(original.read_bytes()) if original.is_file() else None
            if baseline.get(path) != original_version:
                raise ValueError("原件已改变，修改基线冲突，请新建副本")
            edit_text(self._work(row), path, before, after, version)
            self._refresh(row)
            row.status, row.error, row.updated_at = "editing", "", now_iso()
            return self._serialize(session, row)

    def diff(self, identifier):
        with self._lock, self.database.session.begin() as session:
            row = self._row(session, identifier)
            if row.status == "discarded":
                raise ValueError("副本已丢弃")
            baseline = json.loads(row.manifest_json)
            current, files, text = changes_diff(
                safe_path(self._folder(row), "base"),
                self._work(row),
                baseline,
            )
            try:
                conflicts = self._source_conflicts(row)
            except (OSError, ValueError) as error:
                conflicts = [str(error)]
            version = tree_version(current)
            if row.status != "verifying" and version != row.change_version:
                row.status, row.change_version = "editing", version
            row.files_changed = len(files)
            return {
                "diff": text,
                "files": files,
                "conflicts": conflicts,
                "source_unchanged": not conflicts,
                "change_version": version,
            }

    def export(self, identifier):
        with self._lock, self.database.session() as session:
            row = self._row(session, identifier)
            if row.status == "discarded":
                raise ValueError("副本已丢弃")
            if row.status == "verifying":
                raise ValueError("验证中不能导出可能仍在改变的副本，请等待验证结束")
            return export_patch(
                safe_path(self._folder(row), "base"),
                self._work(row),
                json.loads(row.manifest_json),
            )

    def discard(self, identifier):
        with self._lock, self.database.session.begin() as session:
            row = self._row(session, identifier)
            self._editable(row)
            folder = self._folder(row)
            if folder.exists():
                # 日志保留在数据库绑定的独立目录，丢弃只删除源码副本。
                for name in ("base", "work"):
                    target = safe_path(folder, name)
                    if target.exists():
                        remove_copy(folder, target)
            row.status, row.updated_at = "discarded", now_iso()
            return self._serialize(session, row)

    def profiles(self):
        with self.database.session() as session:
            return [
                self._profile(row)
                for row in session.scalars(
                    select(VerificationProfileRecord)
                    .where(
                        VerificationProfileRecord.project_id == self.project_id,
                    )
                    .order_by(VerificationProfileRecord.name)
                )
            ]

    @staticmethod
    def _profile(row):
        return {
            "id": row.id,
            "name": row.name,
            "argv": json.loads(row.argv_json),
            "timeout_seconds": row.timeout_seconds,
        }

    def save_profile(self, name, argv, timeout_seconds=120, identifier=None):
        body = ProfileWrite(id=identifier, name=name, argv=argv, timeout_seconds=timeout_seconds)
        if any(not value or "\x00" in value or len(value) > 20000 for value in body.argv):
            raise ValueError("验证参数不能为空或含 NUL，单项不能超过 20000 字符")
        if not body.name.strip():
            raise ValueError("验证配置名称不能为空")
        executable = shutil.which(body.argv[0])
        if executable is None:
            raise ValueError("验证程序不存在，请填写已安装程序的路径")
        arguments = [str(Path(executable).resolve()), *body.argv[1:]]
        with self._lock, self.database.session.begin() as session:
            row = session.get(VerificationProfileRecord, (body.id or new_id(), self.project_id))
            if row is None:
                row = VerificationProfileRecord(id=body.id or new_id(), project_id=self.project_id)
                session.add(row)
            row.name, row.argv_json = body.name.strip(), json.dumps(arguments)
            row.timeout_seconds, row.updated_at = body.timeout_seconds, now_iso()
            session.flush()
            return self._profile(row)

    def verify(self, identifier, profile_id):
        with self._lock:
            if self._closed:
                raise ValueError("服务正在关闭")
            project_id = self.project_id
            with self.database.session.begin() as session:
                row = self._row(session, identifier, project_id)
                self._editable(row)
                profile = session.get(VerificationProfileRecord, (profile_id, project_id))
                if profile is None:
                    raise FileNotFoundError("验证配置不存在，请先由管理员配置")
                if self._source_conflicts(row):
                    raise ValueError("原件已改变，修改基线冲突，请新建副本再验证")
                version = self._refresh(row)
                verification = VerificationRecord(
                    id=new_id(),
                    project_id=project_id,
                    change_id=row.id,
                    status="running",
                    profile_id=profile.id,
                    argv_json=profile.argv_json,
                    timeout_seconds=profile.timeout_seconds,
                    change_version=version,
                )
                session.add(verification)
                row.latest_verification_id = verification.id
                row.status, row.error, row.updated_at = "verifying", "", now_iso()
                task = VerificationTask(project_id, row.id, verification.id)
                folder = self._folder(row)
                logs = safe_path(folder, "logs")
                logs.mkdir(exist_ok=True)
                log_path = safe_path(logs, f"{verification.id}.log")
                work = self._work(row)
                argv, timeout = json.loads(profile.argv_json), profile.timeout_seconds
            self._tasks[task.verification_id] = task
            task.thread = threading.Thread(
                target=self._run,
                args=(task, argv, timeout, work, log_path),
                daemon=True,
                name=f"code-verification-{task.verification_id}",
            )
            task.thread.start()
            return self.get(identifier)

    def _run(self, task, argv, timeout, work, log_path):
        status, exit_code, error = "failed", None, ""
        try:
            status, exit_code, error = run_process(task, argv, work, log_path, timeout)
        except Exception as failure:
            error = f"验证进程执行失败：{failure}"
        try:
            with self._lock, self.database.session.begin() as session:
                row = self._row(session, task.change_id, task.project_id)
                verification = session.get(VerificationRecord, task.verification_id)
                if verification is None or verification.project_id != task.project_id:
                    return
                if verification.status != "running":
                    return
                try:
                    if self._refresh(row) != verification.change_version:
                        status, error = "failed", "验证期间副本发生改变，请重新检查并验证"
                    if self._source_conflicts(row):
                        status, error = "failed", "原件在验证期间改变，当前结果不能作为验收依据"
                except (OSError, ValueError) as failure:
                    status, error = "failed", f"验证后的副本边界检查失败：{failure}"
                verification.status, verification.exit_code = status, exit_code
                verification.error, verification.ended_at = error, now_iso()
                row.status = "passed" if status == "passed" else "failed"
                row.error, row.updated_at = error, now_iso()
        finally:
            task.finished.set()

    def cancel(self, identifier):
        with self._lock, self.database.session() as session:
            row = self._row(session, identifier)
            if row.status != "verifying":
                raise ValueError("没有正在执行的验证")
            task = self._tasks.get(row.latest_verification_id)
            if task is None or task.project_id != row.project_id:
                raise ValueError("验证已中断，请恢复记录后重试")
            task.cancel.set()
            return self._serialize(session, row)

    async def wait(self, identifier, timeout_seconds=60):
        row = await asyncio.to_thread(self.get, identifier)
        latest = row["latest_verification"]
        task = self._tasks.get(latest["id"]) if latest else None
        if task:
            await asyncio.to_thread(task.finished.wait, max(0, timeout_seconds))
        return await asyncio.to_thread(self.get, identifier)

    def recover(self, all_projects=False):
        with self._lock, self.database.session.begin() as session:
            query = select(VerificationRecord).where(VerificationRecord.status == "running")
            if not all_projects:
                query = query.where(VerificationRecord.project_id == self.project_id)
            recovered = 0
            for verification in session.scalars(query):
                if (
                    verification.id in self._tasks
                    and not self._tasks[verification.id].finished.is_set()
                ):
                    continue
                verification.status, verification.ended_at = "interrupted", now_iso()
                verification.error = "服务重启，原验证已中断；不会自动重新执行命令"
                row = self._row(session, verification.change_id, verification.project_id)
                if row.latest_verification_id == verification.id:
                    row.status, row.error = "interrupted", verification.error
                    row.updated_at = now_iso()
                recovered += 1
            return recovered

    async def shutdown(self):
        with self._lock:
            self._closed = True
            tasks = [task for task in self._tasks.values() if not task.finished.is_set()]
            for task in tasks:
                task.cancel.set()
        await asyncio.gather(*(asyncio.to_thread(task.finished.wait, 12) for task in tasks))

    def log_path(self, identifier, verification_id=None):
        with self.database.session() as session:
            row = self._row(session, identifier)
            verification = session.scalar(
                select(VerificationRecord).where(
                    VerificationRecord.id == (verification_id or row.latest_verification_id),
                    VerificationRecord.project_id == row.project_id,
                    VerificationRecord.change_id == row.id,
                )
            )
            if verification is None:
                raise FileNotFoundError("验证记录不存在")
            target = safe_path(self._folder(row), f"logs/{verification.id}.log")
            if not target.is_file():
                raise FileNotFoundError("验证日志尚未生成")
            return target

    def _serialize(self, session, row):
        latest = None
        if row.latest_verification_id:
            verification = session.scalar(
                select(VerificationRecord).where(
                    VerificationRecord.id == row.latest_verification_id,
                    VerificationRecord.project_id == row.project_id,
                    VerificationRecord.change_id == row.id,
                )
            )
            if verification:
                latest = self._verification(row, verification)
        return {
            "id": row.id,
            "title": row.title,
            "goal": row.goal,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "files_changed": row.files_changed,
            "change_version": row.change_version,
            "latest_verification": latest,
            "error": row.error,
        }

    def _verification(self, row, verification):
        output, truncated = "", False
        log = safe_path(self._folder(row), f"logs/{verification.id}.log")
        if log.is_file():
            with log.open("rb") as stream:
                size = log.stat().st_size
                truncated = size > OUTPUT_BYTES
                stream.seek(max(0, size - OUTPUT_BYTES))
                output = stream.read(OUTPUT_BYTES).decode("utf-8", errors="replace")
        return {
            "id": verification.id,
            "status": verification.status,
            "profile_id": verification.profile_id,
            "argv": json.loads(verification.argv_json),
            "exit_code": verification.exit_code,
            "output": output,
            "truncated": truncated,
            "started_at": verification.started_at,
            "ended_at": verification.ended_at,
            "change_version": verification.change_version,
            "stale": verification.change_version != row.change_version,
            "error": verification.error,
        }
