"""对话权限内的代码工作 API；配置入口单独要求管理员身份。"""

import asyncio

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.modules.auth.router import identity, require_admin
from app.modules.code_work.checks import RequirementWrite
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


class HunkRevert(FileRevert):
    hunk_id: str = Field(min_length=64, max_length=64)


class DirectoryOpen(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: str = Field(pattern="^(source|workspace)$")


class MergeResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choice: str = Field(pattern="^(source|workspace|manual)$")
    content: str = Field(default="", max_length=2_000_000)


class MergePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paths: list[str] | None = Field(default=None, min_length=1, max_length=1000)
    resolutions: dict[str, MergeResolution] = Field(default_factory=dict, max_length=1000)


class MergeConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_target: str = Field(min_length=1, max_length=1024)


class RecoveryConfirm(MergeConfirm):
    versions: dict[str, str] = Field(max_length=1000)


class RequirementDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-f0-9]{32}$")
    version: str = Field(min_length=64, max_length=64)


class DesktopFlowWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    revision: int = Field(ge=0)


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
    async def summary(thread_id: str, run_id: str = Query(default="", max_length=64)):
        return await asyncio.to_thread(work.summary, thread_id, run_id)

    @router.put(prefix + "/file")
    async def write(thread_id: str, body: FileWrite):
        return await asyncio.to_thread(work.write, thread_id, body.path, body.content, body.version)

    @router.get(prefix + "/diff")
    async def diff(thread_id: str, path: str, run_id: str = Query(default="", max_length=64)):
        return await asyncio.to_thread(work.diff, thread_id, path, run_id)

    @router.post(prefix + "/open-directory")
    async def open_directory(thread_id: str, body: DirectoryOpen):
        return await asyncio.to_thread(work.open_directory, thread_id, body.location)

    @router.post(prefix + "/revert-hunk")
    async def revert_hunk(thread_id: str, body: HunkRevert):
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后撤销")
        return await asyncio.to_thread(
            work.revert_hunk, thread_id, body.path, body.version, body.hunk_id
        )

    @router.post(prefix + "/merge/preview")
    async def merge_preview(thread_id: str, body: MergePreview):
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后生成合并预览")
        return await asyncio.to_thread(
            work.merge_preview,
            thread_id,
            body.paths,
            {path: item.model_dump() for path, item in body.resolutions.items()},
        )

    @router.get(prefix + "/merge/{plan_id}")
    async def merge_status(thread_id: str, plan_id: str):
        return await asyncio.to_thread(work.merge_status, thread_id, plan_id)

    @router.get(prefix + "/merge/{plan_id}/diff")
    async def merge_diff(thread_id: str, plan_id: str, path: str):
        return await asyncio.to_thread(work.merge_diff, thread_id, plan_id, path)

    @router.post(prefix + "/merge/{plan_id}/verify", status_code=202)
    async def merge_verify(thread_id: str, plan_id: str):
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后验证合并结果")
        return await work.merge_verify(thread_id, plan_id)

    @router.post(prefix + "/merge/{plan_id}/apply")
    async def merge_apply(thread_id: str, plan_id: str, body: MergeConfirm, request: Request):
        require_admin(request)
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后应用")
        plan = await asyncio.to_thread(work.merge_status, thread_id, plan_id)
        if body.confirm_target != plan["target"]:
            raise ValueError("确认的原工程目录与预览不一致")
        user = identity(request)["user"]
        return await asyncio.to_thread(
            work.merge_apply, thread_id, plan_id, {"id": user["id"], "name": user["username"]}
        )

    @router.post(prefix + "/merge/{plan_id}/rollback")
    async def merge_rollback(thread_id: str, plan_id: str, body: MergeConfirm, request: Request):
        require_admin(request)
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后回退")
        plan = await asyncio.to_thread(work.merge_status, thread_id, plan_id)
        if body.confirm_target != plan["target"]:
            raise ValueError("确认的原工程目录与记录不一致")
        user = identity(request)["user"]
        return await asyncio.to_thread(
            work.merge_rollback, thread_id, plan_id, {"id": user["id"], "name": user["username"]}
        )

    @router.post(prefix + "/revert")
    async def revert(thread_id: str, body: FileRevert):
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后撤销，避免覆盖正在生成的修改")
        return await asyncio.to_thread(work.revert, thread_id, body.path, body.version)

    @router.get(prefix + "/recovery/{recovery_id}/diff")
    async def recovery_diff(thread_id: str, recovery_id: str, path: str):
        return await asyncio.to_thread(work.recovery_diff, thread_id, recovery_id, path)

    @router.post(prefix + "/recovery/{recovery_id}/resolve")
    async def recovery_resolve(
        thread_id: str, recovery_id: str, body: RecoveryConfirm, request: Request
    ):
        require_admin(request)
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后处理恢复冲突")
        user = identity(request)["user"]
        return await asyncio.to_thread(
            work.recovery_resolve,
            thread_id,
            recovery_id,
            body.confirm_target,
            body.versions,
            {"id": user["id"], "name": user["username"]},
        )

    @router.post(prefix + "/verify", status_code=202)
    async def verify(thread_id: str):
        return await work.verify(thread_id)

    @router.put(prefix + "/requirement")
    async def set_requirement(thread_id: str, body: RequirementWrite):
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后修改测试")
        return await asyncio.to_thread(work.set_requirement, thread_id, body.model_dump())

    @router.post(prefix + "/requirement/delete")
    async def delete_requirement(thread_id: str, body: RequirementDelete):
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后删除测试")
        return await asyncio.to_thread(work.delete_requirement, thread_id, body.id, body.version)

    @router.put(prefix + "/desktop-flow")
    async def desktop_flow(thread_id: str, body: DesktopFlowWrite):
        if services.repository.active_runs(thread_id):
            raise ValueError("请等待聊天运行结束后修改验证范围")
        return await asyncio.to_thread(
            work.set_desktop_flow, thread_id, body.enabled, body.revision
        )

    @router.get(prefix + "/report")
    async def report(
        thread_id: str, job_id: str, name: str = "verification.json", plan_id: str = ""
    ):
        data = await asyncio.to_thread(work.report, thread_id, job_id, name, plan_id)
        return Response(
            data,
            media_type="image/png" if name.endswith(".png") else "application/json",
            headers={"Cache-Control": "private, no-store"},
        )

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
