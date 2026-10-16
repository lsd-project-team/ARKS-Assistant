"""启动器和页面共用的服务状态，独立于用户当前项目。"""

import os

from fastapi import APIRouter

from app.config import PROJECT_ROOT


def create_router(services):
    router = APIRouter()

    @router.get("/api/health")
    async def health():
        return {
            "ok": True,
            "workspace": str(services.paths.workspace),
            "workspace_id": services.workspace.id,
            "project_directory": str(PROJECT_ROOT),
            "data_directory": str(services.paths.data),
            "process_id": os.getpid(),
        }

    return router
