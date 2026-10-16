"""交接工作台 candidates 接口。"""

import asyncio

from fastapi import APIRouter, Depends

from app.modules.auth.router import require_admin
from app.modules.handover.interfaces.http.context import HandoverHTTPContext
from app.modules.handover.interfaces.http.schemas import (
    AIStart,
    Promotion,
)


def register(router: APIRouter, ctx: HandoverHTTPContext):
    store = ctx.repository_factory
    ai = ctx.ai

    @router.post("/ai", status_code=201)
    async def start_ai(body: AIStart):
        return ai.start(store(), body.action, body.record_ids, body.actor)

    @router.post("/ai/{identifier}/cancel")
    async def cancel_ai(identifier: str):
        return await ai.cancel(store(), identifier)

    @router.post(
        "/candidates/{identifier}/promote", status_code=201, dependencies=[Depends(require_admin)]
    )
    async def promote(identifier: str, body: Promotion):
        return await asyncio.to_thread(store().promote, identifier, body, body.title, body.proposed)
