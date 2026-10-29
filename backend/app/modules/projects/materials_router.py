"""资料管理、历史引用和项目导出 API。"""

import asyncio
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.projects.export import export_project
from app.modules.projects.materials import Materials


class MaterialCreate(BaseModel):
    # 创建仅接受文档字段，旧版保存回复的请求不能被静默转成普通文档。
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=500000)
    source_name: str = Field(default="", max_length=250)

    @field_validator("title", "content")
    @classmethod
    def required(cls, value):
        if not value.strip():
            raise ValueError("标题和正文不能为空")
        return value.strip()


class MaterialUpdate(BaseModel):
    version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=500000)
    state: Literal["active", "deleted"] | None = None

    @field_validator("title", "content")
    @classmethod
    def required(cls, value):
        if value is not None and not value.strip():
            raise ValueError("标题和正文不能为空")
        return value.strip() if value else value


def create_router(projects):
    router = APIRouter()

    def store(project_id, *, historical=False):
        projects.get(project_id, include_deleted=historical)
        return Materials(projects.database, project_id)

    @router.get("/api/projects/{project_id}/materials")
    async def listing(project_id: str, state: str = "active", query: str = ""):
        return await asyncio.to_thread(store(project_id).list, state, query)

    @router.post("/api/projects/{project_id}/materials", status_code=201)
    async def create(project_id: str, body: MaterialCreate):
        async with projects.edit_lock:
            projects.snapshot(project_id)
            return store(project_id).create(body)

    @router.get("/api/projects/{project_id}/materials/{material_id}")
    async def read(project_id: str, material_id: str, version: int | None = Query(None, ge=1)):
        return store(project_id, historical=version is not None).read(material_id, version)

    @router.patch("/api/projects/{project_id}/materials/{material_id}")
    async def update(project_id: str, material_id: str, body: MaterialUpdate):
        async with projects.edit_lock:
            projects.snapshot(project_id)
            return store(project_id).update(material_id, body)

    @router.get("/api/projects/{project_id}/export")
    async def export(project_id: str):
        projects.get(project_id)
        payload = await asyncio.to_thread(export_project, projects, project_id)
        return Response(
            payload,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="project-{project_id}.zip"'},
        )

    return router
