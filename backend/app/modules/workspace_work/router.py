"""工作区 API：配置、文件、差异、还原、命令与审批。"""

import asyncio

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.modules.auth.router import identity, require_admin
from app.modules.workspace_work.environment import WorkspaceSettings


class FileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=500)
    version: str = Field(default="", max_length=64)
    content: str = Field(max_length=2_000_000)


class FileEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=500)
    version: str = Field(default="", max_length=64)
    old_text: str = Field(min_length=1, max_length=100_000)
    new_text: str = Field(default="", max_length=2_000_000)


class PatchWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    edits: list[FileEdit] = Field(min_length=1, max_length=50)


class RestoreWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(default="", max_length=500)
    revision: int | None = Field(default=None, ge=0)


class CommandWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    argv: list[str] = Field(min_length=1, max_length=32)
    cwd: str = Field(default="", max_length=500)
    timeout: int | None = Field(default=None, ge=1, le=1800)


class ApprovalWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(approve|deny)$")


def create_router(services):
    router = APIRouter()
    work = services.workspace_work
    prefix = "/api/threads/{thread_id}/workspace-work"

    @router.get("/api/workspace-work")
    async def get_environment(request: Request):
        require_admin(request)
        return await asyncio.to_thread(work.environment.public, work.project())

    @router.put("/api/workspace-work")
    async def set_environment(body: WorkspaceSettings, request: Request):
        require_admin(request)
        return await asyncio.to_thread(
            work.environment.save, work.project(), body, services.paths.data
        )

    @router.get(prefix)
    async def status(thread_id: str):
        return await asyncio.to_thread(work.status, thread_id)

    @router.get(prefix + "/list")
    async def listing(thread_id: str, path: str = ""):
        return await asyncio.to_thread(work.list, thread_id, path)

    @router.get(prefix + "/file")
    async def read(thread_id: str, path: str, start_line: int = 1, end_line: int = 400):
        return await asyncio.to_thread(work.read, thread_id, path, start_line, end_line)

    @router.put(prefix + "/file")
    async def write(thread_id: str, body: FileWrite):
        return await asyncio.to_thread(work.write, thread_id, body.path, body.content, body.version)

    @router.post(prefix + "/edit")
    async def edit(thread_id: str, body: FileEdit):
        return await asyncio.to_thread(
            work.edit, thread_id, body.path, body.old_text, body.new_text, body.version
        )

    @router.post(prefix + "/patch")
    async def patch(thread_id: str, body: PatchWrite):
        return await asyncio.to_thread(
            work.apply_patch, thread_id, [item.model_dump() for item in body.edits]
        )

    @router.get(prefix + "/diff")
    async def diff(thread_id: str, path: str, run_id: str = Query(default="", max_length=64)):
        return await asyncio.to_thread(work.diff, thread_id, path, run_id)

    @router.post(prefix + "/restore")
    async def restore(thread_id: str, body: RestoreWrite):
        return await asyncio.to_thread(work.restore, thread_id, body.path, body.revision)

    @router.get(prefix + "/search")
    async def search(thread_id: str, query: str, limit: int = Query(default=60, ge=1, le=200)):
        return await asyncio.to_thread(work.search, thread_id, query, limit)

    @router.post(prefix + "/command", status_code=202)
    async def command(thread_id: str, body: CommandWrite):
        return await asyncio.to_thread(
            work.run_command, thread_id, body.argv, body.cwd, body.timeout
        )

    @router.get(prefix + "/approvals")
    async def approvals(thread_id: str):
        status = await asyncio.to_thread(work.status, thread_id)
        return {"items": status.get("approvals", [])}

    @router.post(prefix + "/approvals/{approval_id}")
    async def decide(thread_id: str, approval_id: str, body: ApprovalWrite, request: Request):
        user = identity(request)["user"]
        return await asyncio.to_thread(
            work.decide_approval,
            thread_id,
            approval_id,
            body.decision,
            {"id": user["id"], "name": user["username"]},
        )

    return router
