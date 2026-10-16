"""交接工作台 records 接口。"""

import asyncio

from fastapi import APIRouter, Query

from app.modules.handover.application.commands import Write
from app.modules.handover.application.records import RecordService
from app.modules.handover.interfaces.http.context import HandoverHTTPContext


def register(router: APIRouter, ctx: HandoverHTTPContext):
    store = ctx.repository_factory

    @router.post("/records", status_code=201)
    async def create(body: Write):
        return await asyncio.to_thread(RecordService(store()).create, body)

    @router.get("/records/{identifier}")
    async def read(identifier: str, version: int | None = Query(default=None, ge=1)):
        return await asyncio.to_thread(store().get, identifier, version)

    @router.patch("/records/{identifier}")
    async def update(identifier: str, body: Write):
        return await asyncio.to_thread(RecordService(store()).update, identifier, body)
