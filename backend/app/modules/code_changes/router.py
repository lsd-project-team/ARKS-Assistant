"""项目分派下的隔离修改 API。"""

import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response

from app.core.container import AppServices
from app.modules.auth.router import require_admin
from app.modules.code_changes.schemas import ChangeWrite, FileEdit, ProfileWrite, VerificationWrite


def create_router(services: AppServices):
    router = APIRouter(prefix="/api/code-changes", tags=["code-changes"])
    changes = services.runtime.code_changes

    async def mutate(operation, *arguments):
        # 与项目改绑、归档共用同一把锁，检查后到写入之间不能切换项目状态。
        async with services.runs.edit_lock:
            await asyncio.to_thread(services.repository.creation_guard)
            return await asyncio.to_thread(operation, *arguments)

    @router.get("")
    async def list_changes():
        return {"changes": await asyncio.to_thread(changes.list)}

    @router.post("")
    async def create_change(body: ChangeWrite):
        return await mutate(changes.create, body.title, body.goal)

    @router.get("/profiles")
    async def list_profiles():
        return {"profiles": await asyncio.to_thread(changes.profiles)}

    @router.post("/profiles", dependencies=[Depends(require_admin)])
    async def save_profile(body: ProfileWrite):
        return await mutate(
            changes.save_profile,
            body.name,
            body.argv,
            body.timeout_seconds,
            body.id,
        )

    @router.get("/{identifier}")
    async def get_change(identifier: str):
        return await asyncio.to_thread(changes.get, identifier)

    @router.get("/{identifier}/file")
    async def read_file(identifier: str, path: str):
        return await asyncio.to_thread(changes.read_file, identifier, path)

    @router.patch("/{identifier}/file")
    async def edit_file(identifier: str, body: FileEdit):
        return await mutate(
            changes.edit_file,
            identifier,
            body.path,
            body.before,
            body.after,
            body.version,
        )

    @router.get("/{identifier}/diff")
    async def diff(identifier: str):
        return await asyncio.to_thread(changes.diff, identifier)

    @router.get("/{identifier}/export")
    async def export(identifier: str):
        return Response(
            await asyncio.to_thread(changes.export, identifier),
            media_type="text/x-diff",
            headers={"Content-Disposition": 'attachment; filename="changes.patch"'},
        )

    @router.post("/{identifier}/discard")
    async def discard(identifier: str):
        return await mutate(changes.discard, identifier)

    @router.post("/{identifier}/verify")
    async def verify(identifier: str, body: VerificationWrite):
        return await mutate(changes.verify, identifier, body.profile_id)

    @router.post("/{identifier}/cancel")
    async def cancel(identifier: str):
        return await asyncio.to_thread(changes.cancel, identifier)

    @router.get("/{identifier}/verifications/{verification_id}/log")
    async def full_log(identifier: str, verification_id: str):
        path = await asyncio.to_thread(changes.log_path, identifier, verification_id)
        return FileResponse(path, media_type="text/plain", filename="verification.log")

    return router
