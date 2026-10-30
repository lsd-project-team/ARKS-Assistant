"""交接工作台 packages 接口。"""

import asyncio

from fastapi import APIRouter, Query

from app.modules.handover.application.packages import export_package, package_references
from app.modules.handover.interfaces.http.context import HandoverHTTPContext
from app.modules.handover.interfaces.http.responses import attachment
from app.modules.handover.interfaces.http.schemas import (
    PackageCreate,
)


def register(router: APIRouter, ctx: HandoverHTTPContext):
    store = ctx.repository_factory

    @router.post("/packages", status_code=201)
    async def package(body: PackageCreate):
        current = store()
        refs = package_references(current, body.record_ids)
        return current.create(
            "package",
            body.title,
            {"records": refs, "recipient": body.recipient, "scope": body.scope, "gaps": body.gaps},
            body.actor,
        )

    @router.get("/packages/{identifier}/export")
    async def export(
        identifier: str,
        format: str = "docx",
        version: int | None = Query(default=None, ge=1),
    ):
        if format not in {"docx", "zip"}:
            raise ValueError("导出格式必须为 docx 或 zip")
        content = await asyncio.to_thread(
            export_package, store(), identifier, ctx.exporter, format == "zip", version
        )
        media = (
            "application/zip"
            if format == "zip"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        return attachment(content, f"设备软件交接包-{identifier}.{format}", media)
