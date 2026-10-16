"""用户确认的修改经验关联到现有调试库，不将模型推断或失败日志自动录库。"""

import asyncio

from fastapi import APIRouter, Request
from pydantic import Field

from app.modules.auth.router import identity
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import actor_name
from app.modules.handover.domain.schemas import DebugIssue
from app.modules.handover.infrastructure.persistence.repository import HandoverStore


class ExperienceWrite(DebugWrite):
    verification_id: str = Field(min_length=1, max_length=36)
    change_version: str = Field(min_length=1, max_length=64)


def save_experience(services, identifier, body, actor):
    changes = services.runtime.code_changes
    # 与编辑/验证同一把锁，确认的是提交时仍有效的修改版本。
    with changes.lock:
        change = changes.get(identifier)
        verified = change.get("latest_verification") or {}
        if (
            change["status"] != "passed"
            or verified.get("status") != "passed"
            or verified.get("stale")
            or verified.get("id") != body.verification_id
            or verified.get("change_version") != body.change_version
        ):
            raise ValueError("本次验证已失效或尚未通过，请核对最新修改与验证结果")
        current_diff = changes.diff(identifier)
        if current_diff["conflicts"]:
            raise ValueError("源基线已变化，请重新建立并验证修改后再保存经验")
        if (
            current_diff["change_version"] != body.change_version
            or changes.get(identifier)["status"] != "passed"
        ):
            raise ValueError("副本版本已变化，请重新验证后再保存经验")
        if not body.payload.verification.strip():
            raise ValueError("请填写实际验证结果；命令通过不能代替设备验收")
        store = HandoverStore(database=services.database)
        with store.lock:
            for row in store.debug_rows(True):
                payload = row["payload"]
                if (
                    payload.get("source_change_id") == identifier
                    and payload.get("source_verification_id") == body.verification_id
                ):
                    return row
            payload = DebugIssue.model_validate(
                {
                    **body.payload.model_dump(),
                    "origin": "human",
                    "reported_by": actor_name(actor),
                    "original_text": body.payload.problem,
                    "source_project_id": services.repository.project_id or "",
                    "source_change_id": identifier,
                    "source_change_version": body.change_version,
                    "source_verification_id": body.verification_id,
                }
            ).model_dump()
            return store.create("debug_issue", body.title, payload, actor_name(actor))


def create_router(services):
    router = APIRouter(tags=["code-experiences"])

    @router.post("/api/code-changes/{identifier}/experience", status_code=201)
    async def create(identifier: str, body: ExperienceWrite, request: Request):
        async with services.runs.edit_lock:
            await asyncio.to_thread(services.repository.creation_guard)
            return await asyncio.to_thread(
                save_experience, services, identifier, body, identity(request)["user"]
            )

    return router
