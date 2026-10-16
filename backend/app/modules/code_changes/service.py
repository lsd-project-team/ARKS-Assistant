"""隔离副本、乐观补丁和绑定版本的命令验证。"""

import asyncio
import json
import logging
import os
import shutil
import threading
from pathlib import Path

from sqlalchemy import func, select

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
from app.modules.code_changes.policy import WorkPolicy, profile_version
from app.modules.code_changes.processes import VerificationTask, run_process
from app.modules.code_changes.requirements import (
    path_allowed,
    requirement_payload,
    requirements,
    scope_conflicts,
)
from app.modules.code_changes.schemas import ChangeWrite, ProfileWrite
from app.modules.code_changes.verification import execute

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
        self.policy = WorkPolicy(paths, database, lambda: self.project_id)

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

    def create(self, title, goal, **details):
        body = ChangeWrite(title=title, goal=goal, **details)
        if getattr(self.workspace, "attached", {}):
            raise ValueError("隔离修改暂不支持附加源码目录，请使用只关联主目录的项目")
        if self.storage.resolve().is_relative_to(self.workspace.root.resolve()):
            raise ValueError("隔离副本必须放在源码目录之外，请调整项目源码目录")
        project_id = self.project_id
        with self._lock:
            manifest_preview = inventory(self.workspace.root)
            required = (
                sum(
                    safe_path(self.workspace.root, name).stat().st_size for name in manifest_preview
                )
                * 2
            )
            self.policy.check_space(self._scope(project_id), required)
            row = CodeChangeRecord(
                id=new_id(),
                project_id=project_id,
                title=body.title,
                goal=body.goal,
                status="ready",
                source_root=str(self.workspace.root.resolve()),
                requirements_json=json.dumps(requirement_payload(body), ensure_ascii=False),
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
            row.review_json, row.delivered_at = "{}", ""
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
            if not path_allowed(row, path):
                raise ValueError("目标文件不在本次需求约定的修改范围内")
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
                row.review_json, row.delivered_at = "{}", ""
            row.files_changed = len(files)
            return {
                "diff": text,
                "files": files,
                "conflicts": conflicts,
                "source_unchanged": not conflicts,
                "change_version": version,
                "scope_conflicts": scope_conflicts(row, files),
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
            "executor": json.loads(row.executor_json),
            "baseline_required": row.baseline_required,
            "category": row.category,
            "environment_label": row.environment_label,
        }

    def save_profile(self, name, argv, timeout_seconds=120, identifier=None, **options):
        # 内部兼容既有可信命令；HTTP必须显式提交executor，不允许缺省成宿主执行。
        options.setdefault("executor", {"kind": "trusted_host"})
        options.setdefault("baseline_required", False)
        body = ProfileWrite(
            id=identifier, name=name, argv=argv, timeout_seconds=timeout_seconds, **options
        )
        if any(not value or "\x00" in value or len(value) > 20000 for value in body.argv):
            raise ValueError("验证参数不能为空或含 NUL，单项不能超过 20000 字符")
        if not body.name.strip():
            raise ValueError("验证配置名称不能为空")
        arguments = list(body.argv)
        if body.executor.kind == "trusted_host":
            body.executor = body.executor.model_copy(
                update={"platform": "windows" if os.name == "nt" else "linux"}
            )
            executable = shutil.which(body.argv[0])
            if executable is None:
                raise ValueError("验证程序不存在，请填写已安装程序的路径")
            arguments[0] = str(Path(executable).resolve())
        with self._lock, self.database.session.begin() as session:
            row = session.get(VerificationProfileRecord, (body.id or new_id(), self.project_id))
            if row is None:
                row = VerificationProfileRecord(id=body.id or new_id(), project_id=self.project_id)
                session.add(row)
            row.name, row.argv_json = body.name.strip(), json.dumps(arguments)
            row.timeout_seconds, row.updated_at = body.timeout_seconds, now_iso()
            row.executor_json = body.executor.model_dump_json()
            row.baseline_required, row.category = body.baseline_required, body.category
            row.environment_label = body.environment_label.strip()
            session.flush()
            return self._profile(row)

    def verify(self, identifier, profile_id, purpose="change"):
        if purpose not in {"baseline", "change"}:
            raise ValueError("验证用途必须为baseline或change")
        with self._lock:
            if self._closed:
                raise ValueError("服务正在关闭")
            project_id = self.project_id
            with self.database.session.begin() as session:
                # SQLite 提前取得写锁，让不同运行实例的容量检查和登记仍保持原子性。
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                row = self._row(session, identifier, project_id)
                self._editable(row)
                profile = session.get(VerificationProfileRecord, (profile_id, project_id))
                if profile is None:
                    raise FileNotFoundError("验证配置不存在，请先由管理员配置")
                running_count = session.scalar(
                    select(func.count())
                    .select_from(VerificationRecord)
                    .where(
                        VerificationRecord.project_id == project_id,
                        VerificationRecord.status == "running",
                    )
                )
                if running_count >= self.policy.get().max_active_verifications:
                    raise ValueError("项目同时验证任务已达到额度，请等待或取消已有任务")
                self.policy.check_space(self._scope(project_id))
                if self._source_conflicts(row):
                    raise ValueError("原件已改变，修改基线冲突，请新建副本再验证")
                version = self._refresh(row)
                _, changed_files, _ = changes_diff(
                    safe_path(self._folder(row), "base"),
                    self._work(row),
                    json.loads(row.manifest_json),
                )
                if scope_conflicts(row, changed_files):
                    raise ValueError("副本包含超出本次修改范围的文件，请先核对差异")
                snapshot = self._profile(profile)
                verification = VerificationRecord(
                    id=new_id(),
                    project_id=project_id,
                    change_id=row.id,
                    status="running",
                    profile_id=profile.id,
                    argv_json=profile.argv_json,
                    timeout_seconds=profile.timeout_seconds,
                    change_version=version,
                    purpose=purpose,
                    executor_json=profile.executor_json,
                    source_version=tree_version(json.loads(row.manifest_json)),
                    profile_version=profile_version(snapshot),
                )
                session.add(verification)
                row.latest_verification_id = verification.id
                row.review_json, row.delivered_at = "{}", ""
                row.status, row.error, row.updated_at = "verifying", "", now_iso()
                task = VerificationTask(project_id, row.id, verification.id)
                folder = self._folder(row)
                logs = safe_path(folder, "logs")
                logs.mkdir(exist_ok=True)
                log_path = safe_path(logs, f"{verification.id}.log")
                work = self._work(row)
            self._tasks[task.verification_id] = task
            task.thread = threading.Thread(
                target=self._run,
                args=(task, snapshot, work, log_path, purpose),
                daemon=True,
                name=f"code-verification-{task.verification_id}",
            )
            task.thread.start()
            return self.get(identifier)

    def _run(self, task, profile, work, log_path, purpose):
        status, exit_code, error = "failed", None, ""
        try:
            status, exit_code, error = execute(
                self, task, profile, work, log_path, purpose, run_process
            )
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
                    _, changed_files, _ = changes_diff(
                        safe_path(self._folder(row), "base"),
                        self._work(row),
                        json.loads(row.manifest_json),
                    )
                    if scope_conflicts(row, changed_files):
                        status, error = "failed", "验证命令产生了超出约定范围的源码修改"
                except (OSError, ValueError) as failure:
                    status, error = "failed", f"验证后的副本边界检查失败：{failure}"
                verification.status, verification.exit_code = status, exit_code
                if profile["executor"]["kind"] == "container":
                    evidence = getattr(task, "executor_evidence", {})
                    verification.executor_json = json.dumps(
                        {**profile["executor"], "evidence": evidence}
                    )
                    if status == "passed" and not (
                        evidence.get("isolated") and evidence.get("protocol") == 2
                    ):
                        status, error = "failed", "缺少可信隔离执行证明，不能记录为通过"
                        verification.status = status
                verification.error, verification.ended_at = error, now_iso()
                verification.error_category = (
                    "environment_or_baseline"
                    if purpose == "baseline" and status != "passed"
                    else "execution"
                    if status != "passed"
                    else ""
                )
                row.status = (
                    ("editing" if row.files_changed else "ready")
                    if purpose == "baseline"
                    else ("passed" if status == "passed" else "failed")
                )
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
                folder = self._folder(row)
                if folder.is_dir():
                    try:
                        temporary = safe_path(folder, "baseline")
                        if temporary.exists():
                            remove_copy(folder, temporary)
                    except (OSError, ValueError):
                        verification.error += "；基线临时文件边界异常，未自动清理"
                if row.latest_verification_id == verification.id:
                    row.status, row.error = "interrupted", verification.error
                    row.updated_at = now_iso()
                recovered += 1
            return recovered

    def cleanup_executors(self):
        from app.infrastructure.execution import cleanup_orphans

        with self.database.session() as session:
            saved = [row[0] for row in session.query(VerificationRecord.executor_json).all()]
            saved += [
                row[0] for row in session.query(VerificationProfileRecord.executor_json).all()
            ]
        executors = [
            json.loads(value) for value in saved if json.loads(value).get("kind") == "container"
        ]
        active = [key for key, task in self._tasks.items() if not task.finished.is_set()]
        result = cleanup_orphans(executors, digest(str(self.paths.data).encode()), active)
        if result["errors"]:
            logging.getLogger(__name__).warning("部分隔离节点遗留资源未清理，请检查节点连接")
        return result

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
            folder = self._folder(row)
            if not folder.is_dir():
                raise FileNotFoundError("验证临时日志已清理，验证档案仍保留")
            target = safe_path(folder, f"logs/{verification.id}.log")
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
                profile = session.get(
                    VerificationProfileRecord, (verification.profile_id, row.project_id)
                )
                current = bool(profile) and verification.profile_version == profile_version(
                    self._profile(profile)
                )
                latest = self._verification(row, verification, environment_current=current)
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
            **requirements(row),
            "review": (json.loads(row.review_json) or None)
            if not latest or not latest["stale"]
            else None,
            "delivered_at": row.delivered_at or None,
        }

    def _verification(self, row, verification, *, environment_current=True):
        output, truncated = "", False
        folder = self._folder(row)
        log = safe_path(folder, f"logs/{verification.id}.log") if folder.is_dir() else None
        if log is not None and log.is_file():
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
            "stale": not environment_current
            or (
                verification.source_version != tree_version(json.loads(row.manifest_json))
                if verification.purpose == "baseline"
                else verification.change_version != row.change_version
            ),
            "error": verification.error,
            "purpose": verification.purpose,
            "executor": json.loads(verification.executor_json),
            "source_version": verification.source_version,
            "profile_version": verification.profile_version,
            "error_category": verification.error_category,
        }

    def verification_history(self, identifier):
        with self._lock, self.database.session.begin() as session:
            row = self._row(session, identifier)
            if row.status == "passed":
                self._refresh(row)
            profiles = {
                profile.id: profile_version(self._profile(profile))
                for profile in session.scalars(
                    select(VerificationProfileRecord).where(
                        VerificationProfileRecord.project_id == row.project_id
                    )
                )
            }
            records = session.scalars(
                select(VerificationRecord)
                .where(
                    VerificationRecord.change_id == row.id,
                    VerificationRecord.project_id == self.project_id,
                )
                .order_by(VerificationRecord.started_at.desc())
            )
            return {
                "verifications": [
                    self._verification(
                        row,
                        record,
                        environment_current=(
                            record.profile_version == profiles.get(record.profile_id)
                        ),
                    )
                    for record in records
                ]
            }

    def readiness(self):
        from app.modules.code_changes.readiness import inspect_project

        project = inspect_project(self.workspace)
        scope = self._scope(self.project_id)
        policy = self.policy.get()
        tokens = self.policy.tokens()
        with self.database.session() as session:
            active = session.scalar(
                select(func.count())
                .select_from(VerificationRecord)
                .where(
                    VerificationRecord.project_id == self.project_id,
                    VerificationRecord.status == "running",
                )
            )
            changes = session.scalar(
                select(func.count())
                .select_from(CodeChangeRecord)
                .where(CodeChangeRecord.project_id == self.project_id)
            )
        profiles = self.profiles()
        unresolved = ["静态检查不能证明可构建，请先验证原版本基线"]
        if not profiles:
            unresolved.append("尚未配置验证命令和执行环境")
        if any(item.get("requires_windows") for item in project.get("projects", [])):
            unresolved.append(
                "Windows执行适配尚未验收，还需独立节点和匹配的构建环境；"
                "Linux应用服务器不能代替该环境"
            )
        return {
            "project": project,
            "policy": policy.model_dump(),
            "usage": {
                **self.policy.storage(scope),
                "changes": changes,
                "active_verifications": active,
                "reading_reserved_tokens": tokens["reserved_tokens"],
                "reading_token_limit": policy.reading_token_limit,
                "budget_day_utc": tokens["day"],
            },
            "unresolved": unresolved,
        }
