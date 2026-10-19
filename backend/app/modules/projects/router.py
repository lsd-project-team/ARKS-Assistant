"""项目管理入口与固定项目服务的 ASGI 分派。"""

import asyncio
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.modules.auth.ownership import require_source, require_thread
from app.modules.auth.router import require_admin
from app.modules.chat import router as conversations
from app.modules.code_changes import router as code_changes
from app.modules.knowledge import router as knowledge
from app.modules.memory import router as memories
from app.modules.projects import code_experiences
from app.modules.projects.association import repository_name
from app.modules.projects.materials_router import create_router as materials_router
from app.modules.projects.service import Projects
from app.modules.source_analysis import router as workspace
from app.modules.source_analysis.collection import source_prefix
from app.modules.source_analysis.reading import router as project_reading
from app.modules.source_analysis.workspace import Workspace


class SourceFolder(BaseModel):
    root: str = Field(min_length=1, max_length=1024)
    label: str = Field(default="", max_length=80)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)
    source_root: str | None = Field(default=None, max_length=1024)
    instructions: str = Field(default="", max_length=20000)
    deepwiki_repo: str = Field(default="", max_length=200)
    auto_associate: bool = True
    source_folders: list[SourceFolder] = Field(default_factory=list, max_length=8)

    @field_validator("name")
    @classmethod
    def name_required(cls, value):
        if not value.strip():
            raise ValueError("项目名称不能为空")
        return value.strip()

    @field_validator("deepwiki_repo")
    @classmethod
    def valid_repository(cls, value):
        if not value.strip():
            return ""
        normalized = repository_name(value)
        if not normalized:
            raise ValueError("请填写 owner/repository 或 GitHub 仓库地址")
        return normalized


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    source_root: str | None = Field(default=None, max_length=1024)
    instructions: str | None = Field(default=None, max_length=20000)
    deepwiki_repo: str | None = Field(default=None, max_length=200)
    auto_associate: bool = False
    state: Literal["active", "archived"] | None = None
    pinned: bool | None = None
    source_folders: list[SourceFolder] = Field(default_factory=list, max_length=8)

    @field_validator("name", "description", "instructions", "deepwiki_repo", "state", "pinned")
    @classmethod
    def non_null(cls, value):
        if value is None:
            raise ValueError("该字段不能为空")
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("name")
    @classmethod
    def name_required(cls, value):
        if not value:
            raise ValueError("项目名称不能为空")
        return value

    @field_validator("deepwiki_repo")
    @classmethod
    def valid_repository(cls, value):
        return ProjectCreate.valid_repository(value)


class MoveThreads(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=200)
    project_id: str | None = None


class ProjectPosition(BaseModel):
    direction: Literal[-1, 1]


def create_router(projects: Projects):
    router = APIRouter()
    router.include_router(materials_router(projects))

    @router.get("/api/projects")
    async def list_projects(state: str = "active", query: str = ""):
        rows = projects.list(state, query)
        available = {row["id"] for row in rows}
        default = (
            projects.default_id
            if projects.default_id in available
            else (projects.account_defaults.preferred(rows) or (rows[0]["id"] if rows else None))
        )
        return {
            "projects": rows,
            "default_project_id": default,
            "default_source": projects.account_defaults.source(),
        }

    @router.post("/api/projects", status_code=201)
    async def create(body: ProjectCreate, request: Request):
        if (body.source_root or body.source_folders) and not projects.account_defaults.permits(
            body.source_root, body.source_folders
        ):
            require_admin(request)
        async with projects.edit_lock:
            return projects.create(body)

    @router.get("/api/projects/association")
    async def association(
        source_root: str = Query(default="", max_length=1024),
        source_roots: Annotated[list[str] | None, Query(max_length=8)] = None,
    ):
        return await asyncio.to_thread(projects.association, source_root, source_roots or [])

    @router.get("/api/projects/search-threads")
    async def search(
        query: str = "",
        state: str = "active",
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        project_state: Literal["active", "archived"] | None = None,
        view: Literal["archived", "deleted"] | None = None,
        project_id: str | None = None,
    ):
        return projects.search(
            query,
            state,
            limit,
            offset,
            project_state=project_state,
            view=view,
            project_id=project_id,
        )

    @router.post("/api/projects/move-threads")
    async def move(body: MoveThreads):
        async with projects.edit_lock:
            return projects.move(body.ids, body.project_id)

    @router.get("/api/projects/thread-location/{thread_id}")
    async def thread_location(thread_id: str):
        from app.modules.chat.models import Thread

        with projects.database.session() as session:
            thread = session.get(Thread, thread_id)
            require_thread(session, thread)
            if not thread or thread.state == "deleted":
                raise FileNotFoundError("来源对话不存在或已移入回收站")
            return {"project_id": thread.project_id, "id": thread.id}

    @router.get("/api/projects/{project_id}/source-context")
    async def source_context(project_id: str):
        return await asyncio.to_thread(projects.source_context, project_id)

    @router.get("/api/projects/{project_id}")
    async def get(project_id: str):
        row = projects.get(project_id)
        return {
            **row,
            "knowledge_available": projects.knowledge_available(row["source_root"]),
            "source_workspace_id": projects.services(project_id).repository.source_workspace_id,
        }

    @router.patch("/api/projects/{project_id}")
    async def edit(project_id: str, body: ProjectUpdate, request: Request):
        existing = projects.get(project_id)
        changing_root = (
            "source_root" in body.model_fields_set and body.source_root != existing["source_root"]
        )
        changing_folders = (
            "source_folders" in body.model_fields_set
            and [item.model_dump() for item in body.source_folders] != existing["source_folders"]
        )
        if (changing_root or changing_folders) and not projects.account_defaults.permits(
            body.source_root if "source_root" in body.model_fields_set else existing["source_root"],
            body.source_folders
            if "source_folders" in body.model_fields_set
            else existing["source_folders"],
        ):
            # 源码目录决定服务器文件可读范围，普通用户不能把它改为账号数据目录。
            require_admin(request)
        async with projects.edit_lock:
            return projects.update(project_id, body)

    @router.post("/api/projects/{project_id}/position")
    async def position(project_id: str, body: ProjectPosition):
        async with projects.edit_lock:
            return projects.position(project_id, body.direction)

    @router.delete("/api/projects/{project_id}")
    async def remove(project_id: str, disposition: str = "independent"):
        async with projects.edit_lock:
            return projects.remove(project_id, disposition)

    @router.get("/api/sources/{source_id}/file")
    async def original_source(source_id: str, path: str):
        with projects.database.session() as session:
            source = require_source(session, source_id)
            root = source.root
        return Workspace(Path(root)).read(path.removeprefix(source_prefix(source_id)))

    return router


class ProjectDispatcher:
    def __init__(self, projects, exception_handlers):
        self.projects, self.exception_handlers = projects, exception_handlers
        self.apps = {}

    async def __call__(self, scope, receive, send):
        relative = scope["path"][len(scope.get("root_path", "")) :].lstrip("/")
        project_id, separator, path = relative.partition("/")
        try:
            services = self.projects.services(project_id)
        except FileNotFoundError as error:
            await JSONResponse({"detail": str(error)}, status_code=404)(scope, receive, send)
            return
        # 目录改变后会装配新服务；旧运行始终持有旧对象，不全局改写 workspace。
        entry = self.apps.get(project_id)
        if not entry or entry[0] is not services:
            app = FastAPI(exception_handlers=self.exception_handlers)
            modules = [workspace, conversations, memories, knowledge]
            if services.repository.project_id:
                modules += [project_reading, code_changes, code_experiences]
            for module in modules:
                app.include_router(module.create_router(services))
            self.apps[project_id] = (services, app)
        app = self.apps[project_id][1]
        scoped = {
            **scope,
            "path": f"/api/{path}",
            "raw_path": f"/api/{path}".encode(),
            "root_path": "",
        }
        await app(scoped, receive, send)
