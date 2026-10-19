"""项目身份与源码目录分开；每个项目拥有固定服务，运行不会随前台切换。"""

import json
import uuid
from pathlib import Path
from threading import RLock

from sqlalchemy import func, select, update

from app.agents.runtime.engine import AgentRuntime
from app.core.config import Paths
from app.core.container import AppServices
from app.core.identifiers import now_iso
from app.infrastructure.database.serialization import record_dict
from app.modules.auth.ownership import (
    current_owner,
    owner_filter,
    require_project,
    require_thread,
    thread_filter,
    unrestricted,
)
from app.modules.chat.models import Message, QueuedQuestion, Run, Thread
from app.modules.chat.repository import Repository
from app.modules.chat.runs import RunManager
from app.modules.code_changes.models import CodeChangeRecord
from app.modules.memory.service import MemoryService
from app.modules.projects.association import associate_repository
from app.modules.projects.models import Project
from app.modules.projects.ownership import AccountProjects
from app.modules.source_analysis.collection import ProjectAnalysis, SourceCollection
from app.modules.source_analysis.models import SourceWorkspace
from app.modules.source_analysis.reading.models import ProjectReadingJob
from app.modules.source_analysis.workspace import Workspace

INDEPENDENT = "independent"


def source_root(value):
    if not value or not value.strip():
        return None
    folder = Path(value.strip()).expanduser()
    if not folder.is_absolute() or not folder.is_dir():
        raise ValueError("源码目录必须是本机已存在的绝对目录")
    return str(folder.resolve())


def source_folders(items, primary):
    result, seen = [], {primary} if primary else set()
    for item in items:
        root = source_root(item.root)
        if not root or root in seen:
            raise ValueError("源码目录不能为空或重复")
        # 重叠目录会让同一文件出现两种身份，拒绝这种关联。
        if any(
            Path(root).is_relative_to(Path(existing)) or Path(existing).is_relative_to(Path(root))
            for existing in seen
        ):
            raise ValueError("关联目录不能互相包含，请选择并列的源码目录")
        seen.add(root)
        result.append(
            {
                "root": root,
                "label": item.label.strip() or Path(root).name,
                "source_id": Workspace(Path(root)).source_id,
            }
        )
    return result


class Projects:
    def __init__(self, base: AppServices):
        self.base = base
        self.database = base.database
        self.default_id = base.workspace.id
        self.lock = RLock()
        # 移动、归档、切换目录与创建运行使用同一编辑锁，防止检查空闲后的竞态。
        self.edit_lock = base.runs.edit_lock
        self.contexts = {}
        self.retired = []
        self.account_defaults = AccountProjects(self)

    def initialize(self):
        with self.database.session.begin() as session:
            if not session.get(Project, self.default_id):
                session.add(
                    Project(
                        id=self.default_id,
                        name="ZX2200 软件分析",
                        deepwiki_repo=self.base.settings.load().deepwiki_repo,
                        source_root=str(self.base.workspace.root),
                    )
                )
                session.flush()
            if not session.get(SourceWorkspace, self.default_id):
                session.add(SourceWorkspace(id=self.default_id, root=str(self.base.workspace.root)))
            # 保持默认项目的旧 workspace_id，原有 Markdown 记忆和检查点无需复制或改名。
            legacy = list(
                session.scalars(
                    select(Thread).where(
                        Thread.project_id.is_(None), Thread.workspace_id != INDEPENDENT
                    )
                )
            )
            for thread in legacy:
                if not session.get(Project, thread.workspace_id):
                    session.add(
                        Project(id=thread.workspace_id, name="历史工作区", source_root=None)
                    )
                    session.flush()
                thread.project_id = thread.workspace_id
                if thread.workspace_id == self.default_id:
                    session.execute(
                        update(Message)
                        .where(
                            Message.thread_id == thread.id, Message.source_workspace_id.is_(None)
                        )
                        .values(source_workspace_id=self.default_id)
                    )
        self.base.repository.project_id = self.default_id
        self.base.repository.source_workspace_id = self.default_id
        self.base.runs.project_snapshot = lambda: self.snapshot(self.default_id)
        self.base.repository.creation_guard = lambda: self.snapshot(self.default_id)
        default = self.get(self.default_id, include_deleted=True)
        if (
            not default["source_folders"]
            and default["state"] != "deleted"
            and default["source_root"] == str(self.base.workspace.root)
        ):
            self.contexts[self.default_id] = self.base

    def get(self, project_id, *, include_deleted=False):
        with self.database.session() as session:
            row = require_project(session, project_id, include_deleted=include_deleted)
            return record_dict(row)

    def snapshot(self, project_id):
        if project_id == INDEPENDENT:
            return {
                "id": None,
                "name": "独立对话",
                "instructions": "",
                **self.account_defaults.source(),
            }
        project = self.get(project_id)
        if project["state"] != "active":
            raise ValueError("请先恢复项目，再创建或继续对话")
        return {
            key: project[key]
            for key in (
                "id",
                "name",
                "description",
                "instructions",
                "source_root",
                "source_folders",
                "deepwiki_repo",
            )
        }

    def list(self, state="active", query=""):
        if state not in {"active", "archived"}:
            raise ValueError("无效的项目列表类型")
        with self.database.session() as session:
            count = (
                select(func.count(Thread.id))
                .where(Thread.project_id == Project.id, Thread.state != "deleted", thread_filter())
                .scalar_subquery()
            )
            statement = select(Project, count).where(Project.state == state, owner_filter(Project))
            if query.strip():
                statement = statement.where(Project.name.icontains(query.strip(), autoescape=True))
            return [
                {
                    **record_dict(row),
                    "thread_count": total,
                    "knowledge_available": self.knowledge_available(row.source_root),
                }
                for row, total in session.execute(
                    statement.order_by(
                        Project.pinned_order.is_(None),
                        Project.pinned_order,
                        Project.sort_order,
                        Project.id,
                    )
                )
            ]

    def knowledge_available(self, root):
        return bool(root and Path(root).resolve() == self.base.workspace.root)

    def source_context(self, project_id):
        """独立对话与项目共用源码身份；不向独立对话复制项目专属资料。"""
        services = self.services(project_id)
        primary = services.repository.source_workspace_id
        return {
            "scope_id": project_id,
            "source_workspace_id": primary,
            "attached_source_ids": sorted(
                source_id
                for source_id in services.repository.source_workspace_ids
                if source_id and source_id != primary
            ),
            "knowledge_available": self.knowledge_available(str(services.workspace.root)),
        }

    def association(self, primary, folders=()):
        root = source_root(primary)
        extra = [source_root(value) for value in folders if value.strip()]
        with self.database.session() as session:
            known = [
                {"source_root": source, "deepwiki_repo": repo}
                for source, repo in session.execute(
                    select(Project.source_root, Project.deepwiki_repo).where(
                        Project.state != "deleted",
                        Project.source_root.is_not(None),
                        owner_filter(Project),
                    )
                )
            ]
        return {
            "source_root": root,
            "knowledge_available": self.knowledge_available(root),
            **associate_repository([root] if root else list(dict.fromkeys(extra)), known),
        }

    @staticmethod
    def register_sources(session, root, folders):
        sources = [(Workspace(Path(root)).source_id, root)] if root else []
        sources += [(item["source_id"], item["root"]) for item in folders]
        for identifier, path in sources:
            if not session.get(SourceWorkspace, identifier):
                session.add(SourceWorkspace(id=identifier, root=path))

    def create(self, body):
        root = source_root(body.source_root)
        binding = self.account_defaults.source() if not unrestricted() and not root else None
        if binding:
            root = binding["source_root"]
        folders = source_folders(body.source_folders, root)
        repo = body.deepwiki_repo
        if binding and not repo:
            repo = binding["deepwiki_repo"]
        if body.auto_associate and not repo:
            repo = self.association(root, [item["root"] for item in folders])["deepwiki_repo"]
        with self.database.session.begin() as session:
            self.register_sources(session, root, folders)
            row = Project(
                owner_id=current_owner(),
                id=uuid.uuid4().hex,
                name=body.name,
                description=body.description,
                instructions=body.instructions,
                deepwiki_repo=repo,
                source_root=root,
                source_folders_json=json.dumps(folders, ensure_ascii=False),
                sort_order=(
                    session.scalar(
                        select(func.max(Project.sort_order)).where(owner_filter(Project))
                    )
                    or 0
                )
                + 1,
            )
            session.add(row)
            session.flush()
            return record_dict(row)

    def ensure_idle(self, session, project_id):
        if session.scalar(
            select(ProjectReadingJob.id).where(
                ProjectReadingJob.project_id == project_id, ProjectReadingJob.status == "running"
            )
        ):
            raise ValueError("项目仍在阅读源码，请先暂停阅读")
        if session.scalar(
            select(CodeChangeRecord.id).where(
                CodeChangeRecord.project_id == project_id, CodeChangeRecord.status == "verifying"
            )
        ):
            raise ValueError("项目仍在验证修改，请先取消验证或等待完成")
        if session.scalar(
            select(Run.id)
            .join(Thread)
            .where(Thread.workspace_id == project_id, Run.status.in_(["queued", "running"]))
        ):
            raise ValueError("项目中还有正在运行的对话，请停止或等待完成")
        if session.scalar(
            select(QueuedQuestion.id).join(Thread).where(Thread.workspace_id == project_id)
        ):
            raise ValueError("项目中还有待发问题，请先处理队列")

    def update(self, project_id, body):
        changes = body.model_dump(exclude_unset=True)
        auto = changes.pop("auto_associate", False)
        if not changes and not auto:
            raise ValueError("请指定要修改的项目信息")
        if "source_root" in changes:
            changes["source_root"] = source_root(changes["source_root"])
        with self.lock, self.database.session.begin() as session:
            row = require_project(session, project_id)
            primary = changes.get("source_root", row.source_root)
            if "source_folders" in changes:
                changes["source_folders_json"] = json.dumps(
                    source_folders(body.source_folders, primary), ensure_ascii=False
                )
                del changes["source_folders"]
            elif "source_root" in changes:
                from types import SimpleNamespace

                source_folders(
                    [SimpleNamespace(**item) for item in json.loads(row.source_folders_json)],
                    primary,
                )
            if auto:
                folders = json.loads(changes.get("source_folders_json", row.source_folders_json))
                changes["deepwiki_repo"] = self.association(
                    primary, [item["root"] for item in folders]
                )["deepwiki_repo"]
            root_changed = (
                "source_root" in changes and changes["source_root"] != row.source_root
            ) or (
                "source_folders_json" in changes
                and changes["source_folders_json"] != row.source_folders_json
            )
            if root_changed or changes.get("state") == "archived":
                self.ensure_idle(session, project_id)
            pinned = changes.pop("pinned", None)
            if pinned is not None:
                maximum = (
                    session.scalar(
                        select(func.max(Project.pinned_order)).where(owner_filter(Project))
                    )
                    or 0
                )
                row.pinned_order = (row.pinned_order or maximum + 1) if pinned else None
            for key, value in changes.items():
                setattr(row, key, value)
            if root_changed:
                session.execute(
                    update(Thread)
                    .where(Thread.project_id == project_id)
                    .values(context_generation=Thread.context_generation + 1)
                )
            row.updated_at = now_iso()
            result = record_dict(row)
        if root_changed and project_id in self.contexts:
            self.retired.append(self.contexts.pop(project_id))
        return result

    def position(self, project_id, direction):
        with self.lock, self.database.session.begin() as session:
            row = require_project(session, project_id)
            pinned = row.pinned_order is not None
            same_group = (
                Project.pinned_order.is_not(None) if pinned else Project.pinned_order.is_(None)
            )
            order = Project.pinned_order if pinned else Project.sort_order
            rows = list(
                session.scalars(
                    select(Project)
                    .where(Project.state == row.state, same_group, owner_filter(Project))
                    .order_by(order, Project.id)
                )
            )
            index = next(index for index, item in enumerate(rows) if item.id == project_id)
            target = index + direction
            if 0 <= target < len(rows):
                rows[index], rows[target] = rows[target], rows[index]
                for position, item in enumerate(rows):
                    setattr(item, "pinned_order" if pinned else "sort_order", position + 1)
            return {"ok": True}

    def move(self, ids, destination):
        target = self.get(destination) if destination else None
        if target:
            self.snapshot(destination)
        context_id = destination or INDEPENDENT
        with self.lock, self.database.session.begin() as session:
            rows = list(session.scalars(select(Thread).where(Thread.id.in_(ids))))
            if len(rows) != len(set(ids)):
                raise FileNotFoundError("部分对话不存在，请刷新列表")
            for row in rows:
                require_thread(session, row)
                if target and row.owner_id is not None and row.owner_id != target["owner_id"]:
                    raise ValueError("只能将对话移动到同一账号的项目")
                if row.state == "deleted":
                    raise ValueError("请先恢复回收站中的对话")
                Repository.ensure_idle(session, row.id)
                if session.scalar(
                    select(QueuedQuestion.id).where(QueuedQuestion.thread_id == row.id)
                ):
                    raise ValueError("此对话还有等待发送的问题，请先清空队列再移动")
            for row in rows:
                if row.workspace_id != context_id:
                    row.context_generation += 1
                row.project_id, row.workspace_id = destination, context_id
                row.updated_at = now_iso()
            return {"moved": len(rows), "project_id": destination}

    def remove(self, project_id, disposition):
        if disposition not in {"independent", "trash"}:
            raise ValueError("请选择将对话移至独立对话或回收站")
        with self.lock, self.database.session.begin() as session:
            project = require_project(session, project_id)
            self.ensure_idle(session, project_id)
            rows = list(session.scalars(select(Thread).where(Thread.project_id == project_id)))
            if session.scalar(
                select(QueuedQuestion.id).join(Thread).where(Thread.project_id == project_id)
            ):
                raise ValueError("项目中有等待发送的问题，请先处理队列")
            for row in rows:
                row.context_generation += 1
                row.project_id, row.workspace_id = None, INDEPENDENT
                if disposition == "trash":
                    row.state, row.deleted_at, row.queue_paused = "deleted", now_iso(), True
            # 保留项目档案与源码身份，原有记忆及引用可以追溯；永远不删除真实源码。
            project.state, project.updated_at = "deleted", now_iso()
        return {"ok": True, "thread_count": len(rows)}

    def services(self, project_id):
        with self.lock:
            project = None if project_id == INDEPENDENT else self.get(project_id)
            if project_id in self.contexts:
                return self.contexts[project_id]
            root = (
                self.base.workspace.root
                if project_id == INDEPENDENT
                else Path(project["source_root"])
                if project and project["source_root"]
                else None
            )
            if root is None:
                root = self.base.paths.data / "empty-workspaces" / project_id
                root.mkdir(parents=True, exist_ok=True)
            paths = Paths(self.base.paths.data, root)
            folders = project["source_folders"] if project else []
            workspace = SourceCollection(root, folders) if folders else Workspace(root)
            source_id = (
                workspace.id
                if project_id == INDEPENDENT or (project and project["source_root"])
                else None
            )
            if source_id or folders:
                with self.database.session.begin() as session:
                    for key, folder in [
                        (source_id, str(root.resolve())),
                        *[(item["source_id"], item["root"]) for item in folders],
                    ]:
                        if key and not session.get(SourceWorkspace, key):
                            session.add(SourceWorkspace(id=key, root=folder))
            # 目录可被多个项目共用，项目记忆和对话仍按项目身份隔离。
            workspace.id = project_id
            repository = Repository(
                self.database,
                project_id,
                project_id=project_id if project else None,
                source_workspace_id=source_id,
            )
            repository.source_workspace_ids = {source_id, *[item["source_id"] for item in folders]}
            memories = MemoryService(paths, self.database, workspace)
            memories.lock = self.base.memories.lock
            runtime = AgentRuntime(paths, self.base.settings, workspace, repository, memories)
            if folders:
                runtime.semantic = ProjectAnalysis(workspace)
            if not self.knowledge_available(str(root)):
                runtime.knowledge.path = paths.data / "unconfigured-project-knowledge.json"
            runs = RunManager(repository, runtime, self.base.settings)
            runs.capacity, runs.edit_lock = self.base.runs.capacity, self.edit_lock
            runtime.project_lock = self.edit_lock
            runs.project_snapshot = lambda: self.snapshot(project_id)
            repository.creation_guard = runs.project_snapshot
            services = AppServices(
                paths,
                self.base.settings,
                self.database,
                workspace,
                repository,
                memories,
                runtime,
                runs,
            )
            self.contexts[project_id] = services
            return services

    def search(
        self,
        query,
        state="active",
        limit=50,
        offset=0,
        *,
        project_state=None,
        view=None,
        project_id=None,
    ):
        # 在数据库中统一排序分页，避免每个项目取前 200 条后丢失更早的命中。
        projects = (
            self.list(project_state)
            if project_state
            else self.list("active") + self.list("archived")
        )
        names = {row["id"]: row["name"] for row in projects}
        workspace_ids = [*names, *([INDEPENDENT] if project_state != "archived" else [])]
        if project_id is not None:
            if project_id != INDEPENDENT:
                self.get(project_id)
            workspace_ids = [project_id] if project_id in workspace_ids else []
        # 归档视图包含归档会话及归档项目下仍为 active 的会话，删除会话始终排除。
        archived_ids = [row["id"] for row in projects if row["state"] == "archived"]
        rows = self.base.repository.catalog.list(
            view or state,
            query,
            limit,
            offset,
            workspace_ids=workspace_ids,
            chronological=True,
            archived_workspace_ids=archived_ids if view == "archived" else None,
        )
        states = {row["id"]: row["state"] for row in projects}
        return [
            dict(
                row,
                project_name=names.get(row["project_id"], "独立对话"),
                project_state=states.get(row["project_id"]),
            )
            for row in rows
        ]

    async def shutdown(self):
        for services in {
            id(item): item for item in [self.base, *self.contexts.values(), *self.retired]
        }.values():
            await services.runs.shutdown()
            await services.runtime.project_reading.shutdown()
            await services.runtime.code_changes.shutdown()
            services.runtime.semantic.close()
