"""可恢复的阅读任务；源码清单、模型分析和人工评审独立计数。"""

import asyncio
import json
from collections import defaultdict
from threading import RLock

from sqlalchemy import select, update

from app.core.config import dump_json
from app.core.identifiers import now_iso
from app.modules.source_analysis.reading import sources
from app.modules.source_analysis.reading.knowledge import knowledge_prompt
from app.modules.source_analysis.reading.models import (
    ProjectReadingDocument,
    ProjectReadingFile,
    ProjectReadingJob,
)
from app.modules.source_analysis.reading.worker import run_reading
from app.modules.source_analysis.workspace import content_version


class ProjectReading:
    def __init__(self, paths, database, workspace, project_id):
        self.paths, self.database, self.workspace = paths, database, workspace
        self._project_id = project_id
        self.analyzer = None
        self.lock = RLock()
        self.tasks = {}
        self.stop_status = {}

    @property
    def project_id(self):
        value = self._project_id() if callable(self._project_id) else self._project_id
        if not value:
            raise ValueError("项目身份不能为空")
        return str(value)

    def bind_project(self, project_id):
        self._project_id = project_id
        return self

    def _query(self, model, project_id=None):
        return select(model).where(model.project_id == (project_id or self.project_id))

    def _job(self, session, identifier, project_id=None):
        row = session.scalar(
            self._query(ProjectReadingJob, project_id).where(ProjectReadingJob.id == identifier)
        )
        if not row:
            raise FileNotFoundError("项目阅读任务不存在")
        return row

    def _files(self, session, identifier, project_id=None):
        return list(
            session.scalars(
                self._query(ProjectReadingFile, project_id)
                .where(ProjectReadingFile.job_id == identifier)
                .order_by(ProjectReadingFile.path)
            )
        )

    def _documents(self, session, identifier, project_id=None, *, latest=True):
        query = self._query(ProjectReadingDocument, project_id).where(
            ProjectReadingDocument.job_id == identifier
        )
        if latest:
            query = query.where(ProjectReadingDocument.latest.is_(True))
        return list(
            session.scalars(
                query.order_by(ProjectReadingDocument.path, ProjectReadingDocument.chunk_index)
            )
        )

    def create(self, title="项目全量阅读"):
        title = title.strip() or "项目全量阅读"
        if len(title) > 200:
            raise ValueError("任务名称最多 200 字")
        project_id = self.project_id
        rows = sources.snapshot(self.workspace)
        with self.lock, self.database.session.begin() as session:
            job = ProjectReadingJob(
                project_id=project_id, title=title, snapshot_version=self._snapshot_version(rows)
            )
            session.add(job)
            session.flush()
            for row in rows:
                session.add(ProjectReadingFile(project_id=project_id, job_id=job.id, **row))
            identifier = job.id
        return self.get(identifier)

    @staticmethod
    def _snapshot_version(rows):
        return content_version(
            dump_json(
                [(row["path"], row["source_version"], row["status"] == "excluded") for row in rows]
            ).encode()
        )

    def list(self):
        with self.lock, self.database.session() as session:
            jobs = session.scalars(
                self._query(ProjectReadingJob).order_by(
                    ProjectReadingJob.created_at.desc(), ProjectReadingJob.id
                )
            )
            rows = [self._public_job(job, self._files(session, job.id)) for job in jobs]
            return {"jobs": rows, "latest": rows[0] if rows else None}

    def get(self, identifier):
        with self.lock, self.database.session() as session:
            job = self._job(session, identifier)
            return self._public_job(job, self._files(session, identifier))

    def files(self, identifier):
        with self.lock, self.database.session() as session:
            self._job(session, identifier)
            return [
                {
                    key: getattr(row, key)
                    for key in (
                        "id",
                        "path",
                        "module",
                        "status",
                        "source_version",
                        "indexed",
                        "read",
                        "analyzed",
                        "reviewed",
                        "stale",
                        "next_chunk",
                        "read_chunks",
                        "error",
                    )
                }
                for row in self._files(session, identifier)
            ]

    @staticmethod
    def _public_job(job, files):
        counts = dict(
            files=len(files),
            indexed=0,
            read=0,
            analyzed=0,
            reviewed=0,
            pending=0,
            failed=0,
            excluded=0,
            stale=0,
        )
        modules = defaultdict(
            lambda: dict(total=0, read=0, analyzed=0, reviewed=0, pending=0, failed=0, stale=0)
        )
        for row in files:
            excluded = row.status == "excluded"
            counts["excluded"] += int(excluded)
            for key in ("indexed", "read", "analyzed", "reviewed", "stale"):
                counts[key] += int(getattr(row, key))
            counts["failed"] += int(row.status == "failed")
            counts["pending"] += int(not excluded and not row.analyzed)
            module = modules[row.module]
            module["total"] += 1
            for key in ("read", "analyzed", "reviewed", "stale"):
                module[key] += int(getattr(row, key))
            module["pending"] += int(not excluded and not row.analyzed)
            module["failed"] += int(row.status == "failed")
        return {
            "id": job.id,
            "title": job.title,
            "status": job.status,
            "snapshot_version": job.snapshot_version,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "counts": counts,
            "modules": [{"name": name, **value} for name, value in sorted(modules.items())],
            "error": job.error,
        }

    @staticmethod
    def _public_document(row):
        result = {
            key: getattr(row, key)
            for key in (
                "id",
                "path",
                "module",
                "version",
                "source_version",
                "start_line",
                "end_line",
                "status",
                "summary",
                "chunk_index",
                "created_at",
                "reviewed_at",
            )
        }
        for name in ("entrypoints", "dependencies", "unknowns", "references"):
            result[name] = json.loads(getattr(row, name + "_json"))
        return result

    def documents(self, identifier):
        with self.lock, self.database.session() as session:
            self._job(session, identifier)
            return [self._public_document(row) for row in self._documents(session, identifier)]

    def review(self, identifier, document_id, version, decision):
        if decision not in {"approved", "needs_changes"}:
            raise ValueError("评审决定无效")
        with self.lock, self.database.session.begin() as session:
            job = self._job(session, identifier)
            if job.status == "running":
                raise ValueError("请暂停阅读后再评审")
            document = session.scalar(
                self._query(ProjectReadingDocument).where(
                    ProjectReadingDocument.job_id == identifier,
                    ProjectReadingDocument.id == document_id,
                )
            )
            if not document:
                raise FileNotFoundError("阅读成果不存在")
            if document.version != version or not document.latest:
                raise ValueError("阅读成果已更新，请重新加载")
            if document.status == "stale" or not self._document_current(session, document):
                raise ValueError("来源已经变化，请刷新阅读任务后重新分析")
            document.status, document.reviewed_at = decision, now_iso()
            # 评审也推进版本，旧窗口不能覆盖另一个人的评审。
            document.version += 1
            file = next(
                row for row in self._files(session, identifier) if row.id == document.file_id
            )
            if decision == "needs_changes":
                file.analyzed, file.reviewed, file.status = False, False, "pending"
                file.next_chunk = min(file.next_chunk, document.chunk_index)
                job.status = "ready"
            else:
                siblings = self._documents(session, identifier)
                file.reviewed = file.analyzed and all(
                    row.status == "approved" for row in siblings if row.file_id == file.id
                )
            job.updated_at = now_iso()
            session.flush()
            result = self._public_document(document)
        return result

    def _document_current(self, session, document, versions=None, files=None, graph=None):
        versions = versions if versions is not None else {}
        if files is None:
            files = {
                row.path: row for row in self._files(session, document.job_id, document.project_id)
            }
        if graph is None:
            graph = self._dependency_graph(
                files, self._documents(session, document.job_id, document.project_id)
            )
        required = {document.path}
        queue = [document.path]
        while queue:
            for dependency in graph.get(queue.pop(), set()) - required:
                required.add(dependency)
                queue.append(dependency)
        for path in required:
            expected = files.get(path)
            if not expected or not expected.indexed:
                return False
            if path not in versions:
                try:
                    versions[path] = sources.describe(self.workspace, path)["source_version"]
                except (OSError, ValueError, UnicodeError):
                    versions[path] = None
            expected_version = (
                document.source_version if path == document.path else (expected.source_version)
            )
            if versions[path] != expected_version:
                return False
        return True

    @staticmethod
    def _dependency_graph(files, documents):
        modules, graph = defaultdict(set), defaultdict(set)
        for path, file in files.items():
            modules[file.module].add(path)
        for document in documents:
            for dependency in json.loads(document.dependencies_json):
                if dependency in files:
                    graph[document.path].add(dependency)
                else:
                    graph[document.path].update(modules.get(dependency, set()))
        return graph

    def refresh(self, identifier):
        with self.lock, self.database.session() as session:
            if self._job(session, identifier).status == "running":
                raise ValueError("请暂停阅读后再刷新")
        rows = sources.snapshot(self.workspace)
        incoming = {row["path"]: row for row in rows}
        with self.lock, self.database.session.begin() as session:
            job = self._job(session, identifier)
            if job.status == "running":
                raise ValueError("请暂停阅读后再刷新")
            files = {row.path: row for row in self._files(session, identifier)}
            changed = {
                path
                for path in files.keys() | incoming.keys()
                if path not in files
                or path not in incoming
                or files[path].source_version != incoming[path]["source_version"]
                or (files[path].status == "excluded") != (incoming[path]["status"] == "excluded")
            }
            documents = self._documents(session, identifier)
            affected = set(changed)
            # 反向依赖闭包：A 变更也使依赖 B→A 的 C→B 成果待重读，循环依赖会收敛。
            while True:
                before = len(affected)
                modules = {sources.module_name(path) for path in affected}
                for document in documents:
                    dependencies = set(json.loads(document.dependencies_json))
                    if document.path in affected or dependencies & (affected | modules):
                        document.status = "stale"
                        affected.add(document.path)
                if len(affected) == before:
                    break
            for path, row in incoming.items():
                file = files.get(path)
                if file is None:
                    file = ProjectReadingFile(project_id=self.project_id, job_id=identifier, **row)
                    session.add(file)
                    continue
                if path in affected or file.status == "failed":
                    for key, value in row.items():
                        setattr(file, key, value)
                    file.read = file.analyzed = file.reviewed = False
                    file.next_chunk = file.read_chunks = 0
                    file.stale = path in affected and any(d.path == path for d in documents)
            for path in files.keys() - incoming.keys():
                file = files[path]
                file.status, file.error, file.stale = "excluded", "源文件或关联目录已删除", True
                file.indexed = file.read = file.analyzed = file.reviewed = False
            job.snapshot_version, job.updated_at = self._snapshot_version(rows), now_iso()
            job.status, job.error = "ready", ""
        return self.get(identifier)

    async def start(self, identifier, analyzer=None, max_chunks=64):
        analyzer = analyzer or self.analyzer
        if analyzer is None:
            raise ValueError("尚未配置源码阅读模型")
        if (
            not isinstance(max_chunks, int)
            or isinstance(max_chunks, bool)
            or not 1 <= max_chunks <= 256
        ):
            raise ValueError("分块预算必须为 1–256 的整数")
        if validate := getattr(analyzer, "validate", None):
            validate()
        project_id = self.project_id
        key = (project_id, identifier)
        with self.lock, self.database.session.begin() as session:
            job = self._job(session, identifier, project_id)
            if key in self.tasks and not self.tasks[key].done():
                return self._public_job(job, self._files(session, identifier, project_id))
            claimed = session.execute(
                update(ProjectReadingJob)
                .where(
                    ProjectReadingJob.id == identifier,
                    ProjectReadingJob.project_id == project_id,
                    ProjectReadingJob.status != "running",
                )
                .values(status="running", error="", updated_at=now_iso())
            )
            if claimed.rowcount != 1:
                raise ValueError("任务仍在其他服务实例中运行")
        task = asyncio.create_task(run_reading(self, identifier, project_id, analyzer, max_chunks))
        self.tasks[key] = task
        task.add_done_callback(lambda done: self._finished(key, done))
        return self.get(identifier)

    def _finished(self, key, task):
        if self.tasks.get(key) is task:
            self.tasks.pop(key, None)
            self.stop_status.pop(key, None)

    async def pause(self, identifier):
        current = self.get(identifier)
        key = (self.project_id, identifier)
        task = self.tasks.get(key)
        if current["status"] == "running" and (task is None or task.done()):
            raise ValueError("任务在其他服务实例运行，不能伪造暂停状态")
        if task and not task.done():
            self.stop_status[key] = "paused"
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        with self.lock, self.database.session.begin() as session:
            job = self._job(session, identifier)
            if job.status in {"running", "ready", "interrupted", "partial", "failed"}:
                job.status, job.updated_at = "paused", now_iso()
        return self.get(identifier)

    def recover(self, all_projects=False):
        with self.lock, self.database.session.begin() as session:
            query = select(ProjectReadingJob) if all_projects else self._query(ProjectReadingJob)
            count = 0
            for job in session.scalars(query.where(ProjectReadingJob.status == "running")):
                if (job.project_id, job.id) in self.tasks:
                    continue
                job.status, job.updated_at, job.error = (
                    "interrupted",
                    now_iso(),
                    "服务停止，阅读可从已保存分块继续",
                )
                count += 1
                for file in self._files(session, job.id, job.project_id):
                    if file.status == "reading":
                        file.status = "pending"
            return count

    async def shutdown(self):
        tasks = list(self.tasks.items())
        for key, task in tasks:
            self.stop_status[key] = "interrupted"
            task.cancel()
        if tasks:
            await asyncio.gather(*(task for _, task in tasks), return_exceptions=True)
        # 刚创建还未来得及进入协程的任务，也必须把 running 持久化为中断。
        with self.lock, self.database.session.begin() as session:
            for (project_id, identifier), _ in tasks:
                job = self._job(session, identifier, project_id)
                if job.status == "running":
                    job.status, job.updated_at = "interrupted", now_iso()

    def prompt(self, query, budget):
        return knowledge_prompt(self, query, budget)

    def tools(self):
        return []
