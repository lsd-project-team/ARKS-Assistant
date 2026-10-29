"""项目资料已退出管理，仅保留旧引用的固定版本读取和项目归档导出。"""

import asyncio

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.modules.projects.export import export_project
from app.modules.projects.materials import Materials


def create_router(projects):
    router = APIRouter()

    @router.get("/api/projects/{project_id}/materials/{material_id}")
    async def read(project_id: str, material_id: str, version: int = Query(ge=1)):
        projects.get(project_id, include_deleted=True)
        return Materials(projects.database, project_id).read(material_id, version)

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
