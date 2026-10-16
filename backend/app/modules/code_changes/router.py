"""项目分派下的隔离修改 API。"""

import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response

from app.core.container import AppServices
from app.modules.auth.router import identity, require_admin
from app.modules.code_changes.delivery import delivery_package, review_change
from app.modules.code_changes.maintenance import cleanup
from app.modules.code_changes.schemas import (
    ChangeWrite,
    CleanupWrite,
    CodeWorkPolicy,
    FileEdit,
    ProfileWrite,
    RequirementsWrite,
    ReviewWrite,
    VerificationWrite,
)


def create_router(services: AppServices):
    router = APIRouter(prefix="/api/code-changes", tags=["code-changes"])
    changes = services.runtime.code_changes

    async def mutate(operation, *arguments, **options):
        # 与项目改绑、归档共用同一把锁，检查后到写入之间不能切换项目状态。
        async with services.runs.edit_lock:
            await asyncio.to_thread(services.repository.creation_guard)
            return await asyncio.to_thread(operation, *arguments, **options)

    @router.get("")
    async def list_changes():
        return {"changes": await asyncio.to_thread(changes.list)}

    @router.post("")
    async def create_change(body: ChangeWrite):
        return await mutate(changes.create, **body.model_dump())

    @router.get("/readiness")
    async def readiness():
        return await asyncio.to_thread(changes.readiness)

    @router.get("/policy")
    async def policy():
        return (await asyncio.to_thread(changes.policy.get)).model_dump()

    @router.put("/policy", dependencies=[Depends(require_admin)])
    async def save_policy(body: CodeWorkPolicy):
        return await mutate(changes.policy.save, body.model_dump())

    @router.post("/cleanup", dependencies=[Depends(require_admin)])
    async def cleanup_copies(body: CleanupWrite):
        return await mutate(cleanup, changes, body.dry_run)

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
            executor=body.executor.model_dump(),
            baseline_required=body.baseline_required,
            category=body.category,
            environment_label=body.environment_label,
        )

    @router.post("/profiles/{profile_id}/probe", dependencies=[Depends(require_admin)])
    async def probe_profile(profile_id: str):
        profiles = await asyncio.to_thread(changes.profiles)
        profile = next((item for item in profiles if item["id"] == profile_id), None)
        if profile is None:
            raise FileNotFoundError("验证配置不存在")
        if profile["executor"]["kind"] != "container":
            return {"available": False, "error": "此配置使用宿主权限，属于非沙箱执行"}
        from app.infrastructure.execution import probe_executor
        from app.modules.code_changes.files import digest

        limits = await asyncio.to_thread(changes.policy.limits)
        executor = {**profile["executor"], "owner_id": digest(str(changes.paths.data).encode())}
        return await asyncio.to_thread(probe_executor, executor, limits)

    @router.get("/{identifier}")
    async def get_change(identifier: str):
        return await asyncio.to_thread(changes.get, identifier)

    @router.get("/{identifier}/file")
    async def read_file(identifier: str, path: str):
        return await asyncio.to_thread(changes.read_file, identifier, path)

    @router.put("/{identifier}/requirements")
    async def update_requirements(identifier: str, body: RequirementsWrite):
        return await mutate(
            changes.update_requirements,
            identifier,
            body.change_version,
            body.requirements_version,
            **body.model_dump(exclude={"change_version", "requirements_version"}),
        )

    @router.patch("/{identifier}/file")
    async def edit_file(identifier: str, body: FileEdit):
        return await mutate(
            changes.edit_file,
            identifier,
            body.path,
            body.before,
            body.after,
            body.version,
            expected_requirements=body.requirements_version,
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
        return await mutate(changes.verify, identifier, body.profile_id, body.purpose)

    @router.get("/{identifier}/verifications")
    async def verifications(identifier: str):
        return await asyncio.to_thread(changes.verification_history, identifier)

    @router.post("/{identifier}/review")
    async def review(identifier: str, body: ReviewWrite, request: Request):
        # 审核人取当前登录身份，表单和模型工具均不能冒名。
        actor = identity(request)["user"]["id"]
        return await mutate(
            review_change,
            changes,
            identifier,
            body.change_version,
            body.requirements_version,
            body.notes,
            actor,
        )

    @router.post("/{identifier}/delivery")
    async def deliver(identifier: str):
        return Response(
            await mutate(delivery_package, changes, identifier),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="code-delivery.zip"'},
        )

    @router.post("/{identifier}/cancel")
    async def cancel(identifier: str):
        return await asyncio.to_thread(changes.cancel, identifier)

    @router.get("/{identifier}/verifications/{verification_id}/log")
    async def full_log(identifier: str, verification_id: str):
        path = await asyncio.to_thread(changes.log_path, identifier, verification_id)
        return FileResponse(path, media_type="text/plain", filename="verification.log")

    return router
