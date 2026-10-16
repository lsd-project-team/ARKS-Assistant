"""只读核对旧版资料的源码指纹，复用当前工作区的路径边界。"""

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.container import AppServices
from app.modules.source_analysis.workspace import Workspace


class SnapshotFile(BaseModel):
    id: str = Field(max_length=80)
    path: str = Field(max_length=1024)
    sha256: str | None = Field(default=None, max_length=64)


class SnapshotCheck(BaseModel):
    files: list[SnapshotFile] = Field(max_length=2048)


def check_files(workspace: Workspace, files: list[SnapshotFile]) -> dict:
    results = {}
    for file in files:
        try:
            source = workspace.read(file.path)
            results[file.id] = {
                "status": "match" if source["version"] == file.sha256 else "changed",
                "version": source["version"],
            }
        except FileNotFoundError:
            results[file.id] = {"status": "missing"}
        except (ValueError, OSError):
            # 访问受限与读取失败都不能被当成「与旧资料一致」。
            results[file.id] = {"status": "unavailable"}
    return results


def create_router(services: AppServices) -> APIRouter:
    router = APIRouter()

    @router.post("/api/knowledge/check")
    async def check(request: SnapshotCheck):
        results = await asyncio.to_thread(check_files, services.workspace, request.files)
        return {"workspace_id": services.workspace.id, "files": results}

    return router
