"""对话权限内的代码工作 API；配置入口单独要求管理员身份。"""

import asyncio

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.modules.auth.router import require_admin
from app.modules.code_work.environment import EnvironmentWrite


class FileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=500)
    version: str = Field(max_length=64)
    content: str = Field(max_length=2_000_000)


class FileRevert(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=500)
    version: str = Field(min_length=64, max_length=64)


def environment_router(services):
    router = APIRouter()
    environment = services.runtime.code_work.environment

    @router.get("/api/settings/code-work")
    async def get_environment(request: Request):
        require_admin(request)
        return environment.public()

    @router.put("/api/settings/code-work")
    async def set_environment(body: EnvironmentWrite, request: Request):
        require_admin(request)
        return await asyncio.to_thread(environment.save, body)

    return router


def create_router(services):
    router = APIRouter()
    work = services.runtime.code_work
    prefix = "/api/threads/{thread_id}/code-work"

    @router.get(prefix)
    async def status(thread_id: str):
        return await asyncio.to_thread(work.status, thread_id)

    @router.post(prefix)
    async def create(thread_id: str):
        return await asyncio.to_thread(work.create, thread_id)

    @router.get(prefix + "/file")
    async def read(thread_id: str, path: str, start_line: int = 1, end_line: int = 300):
        return await asyncio.to_thread(work.read, thread_id, path, start_line, end_line)

    @router.get(prefix + "/summary")
    async def summary(thread_id: str):
        return await asyncio.to_thread(work.summary, thread_id)

    @router.put(prefix + "/file")
    async def write(thread_id: str, body: FileWrite):
        return await asyncio.to_thread(work.write, thread_id, body.path, body.content, body.version)

    @router.get(prefix + "/diff")
    async def diff(thread_id: str, path: str):
        return await asyncio.to_thread(work.diff, thread_id, path)

    @router.post(prefix + "/revert")
    async def revert(thread_id: str, body: FileRevert):
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后撤销，避免覆盖正在生成的修改")
        return await asyncio.to_thread(work.revert, thread_id, body.path, body.version)

    @router.post(prefix + "/verify", status_code=202)
    async def verify(thread_id: str):
        return await work.verify(thread_id)

    @router.post(prefix + "/cancel")
    async def cancel(thread_id: str):
        return work.cancel(thread_id)

    @router.get(prefix + "/export")
    async def export(thread_id: str, revision: int = Query(ge=0)):
        content = await asyncio.to_thread(work.export, thread_id, revision)
        return Response(
            content,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="code-changes.zip"'},
        )

    return router
