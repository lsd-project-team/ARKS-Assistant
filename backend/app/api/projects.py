"""项目管理入口与固定项目服务的 ASGI 分派。"""

import asyncio
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.api import configuration, conversations, knowledge, workspace
from app.api.project_materials import create_router as materials_router
from app.models import SourceWorkspace
from app.project_association import repository_name
from app.projects import Projects
from app.source_collection import source_prefix
from app.workspace import Workspace


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
        return {"projects": projects.list(state, query), "default_project_id": projects.default_id}

    @router.post("/api/projects", status_code=201)
    async def create(body: ProjectCreate):
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
        from app.models import Thread

        with projects.database.session() as session:
            thread = session.get(Thread, thread_id)
            if not thread or thread.state == "deleted":
                raise FileNotFoundError("来源对话不存在或已移入回收站")
            return {"project_id": thread.project_id, "id": thread.id}

    @router.get("/api/projects/{project_id}")
    async def get(project_id: str):
        row = projects.get(project_id)
        return {
            **row,
            "knowledge_available": projects.knowledge_available(row["source_root"]),
            "source_workspace_id": projects.services(project_id).repository.source_workspace_id,
        }

    @router.patch("/api/projects/{project_id}")
    async def edit(project_id: str, body: ProjectUpdate):
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
            source = session.get(SourceWorkspace, source_id)
            if not source:
                raise FileNotFoundError("原始源码工作区不存在")
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
            for module in (workspace, conversations, configuration, knowledge):
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
