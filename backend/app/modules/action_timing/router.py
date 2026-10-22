"""通过现有认证及项目分派接入；上传体按流限制大小。"""

import asyncio
import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.modules.action_timing.catalog import CATALOG
from app.modules.action_timing.packages import MAX_BYTES
from app.modules.action_timing.schemas import Status
from app.modules.action_timing.service import ActionTiming
from app.modules.action_timing.source_service import SourceTiming


def create_router(services):
    router = APIRouter(prefix="/api/action-timing", tags=["action-timing"])
    timing = ActionTiming(services)
    source = SourceTiming(services.workspace, services.paths.data / "cache" / "action-timing")

    def source_scope():
        with services.database.session() as session:
            timing.scope(session)

    @router.get("/source-analysis")
    async def source_analysis():
        source_scope()
        return await asyncio.to_thread(source.summary)

    @router.get("/source-analysis/export")
    async def source_export():
        source_scope()
        return Response(
            await asyncio.to_thread(source.export_csv),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="zx2200-source-action-timing.csv"'
            },
        )

    @router.get("/source-analysis/coverage")
    async def source_coverage():
        source_scope()
        return await asyncio.to_thread(source.coverage)

    @router.get("/source-analysis/{identifier}")
    async def source_detail(identifier: str):
        source_scope()
        return await asyncio.to_thread(source.detail, identifier)

    @router.get("/catalog")
    async def catalog():
        return {"protocol_version": 1, "actions": CATALOG}

    @router.post("/imports", status_code=201)
    async def import_file(request: Request):
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_BYTES:
                raise HTTPException(413, "数据包超过16MiB，请缩小采集批次")
            raw.extend(chunk)
        return await asyncio.to_thread(timing.import_package, bytes(raw))

    @router.get("/runs")
    async def runs(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        return await asyncio.to_thread(timing.runs, limit, offset)

    @router.get("/runs/{identifier}/summary")
    async def summary(identifier: str):
        return await asyncio.to_thread(timing.summary, identifier)

    @router.get("/runs/{identifier}/events")
    async def events(
        identifier: str,
        action_code: str = Query("", max_length=100),
        status: Status | None = None,
        kind: Literal["action", "stage"] = "action",
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        return await asyncio.to_thread(
            timing.events, identifier, action_code, status, kind, limit, offset
        )

    @router.get("/runs/{identifier}/events/{event_id}")
    async def detail(identifier: str, event_id: str):
        return await asyncio.to_thread(timing.detail, identifier, event_id)

    @router.get("/runs/{identifier}/export")
    async def export(identifier: str, format: Literal["json", "csv"] = "json"):
        content = (
            await asyncio.to_thread(timing.export_csv, identifier)
            if format == "csv"
            else json.dumps(await asyncio.to_thread(timing.package, identifier), ensure_ascii=False)
        )
        return Response(
            content,
            media_type="text/csv" if format == "csv" else "application/json",
            headers={
                "Content-Disposition": f'attachment; filename="action-timing-{identifier}.{format}"'
            },
        )

    return router
