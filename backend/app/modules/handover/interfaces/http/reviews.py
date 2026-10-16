"""交接工作台 reviews 接口。"""

import asyncio

from fastapi import APIRouter, Depends, Request

from app.modules.auth.router import require_admin
from app.modules.handover.application.commands import Action
from app.modules.handover.interfaces.http.context import HandoverHTTPContext


def register(router: APIRouter, ctx: HandoverHTTPContext):
    store = ctx.repository_factory

    @router.get("/records/{identifier}/history", dependencies=[Depends(require_admin)])
    async def history(identifier: str):
        return await asyncio.to_thread(store().history, identifier)

    @router.post("/records/{identifier}/{action}")
    async def action(identifier: str, action: str, body: Action, request: Request):
        if action in {"confirm", "reject"}:
            require_admin(request)
        return await asyncio.to_thread(store().action, identifier, action, body)

    @router.get("/events", dependencies=[Depends(require_admin)])
    async def events():
        return await asyncio.to_thread(store().events)
