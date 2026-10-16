"""交接工作台 debug_issues 接口。"""

import asyncio

from fastapi import APIRouter, Request

from app.modules.auth.router import identity
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.interfaces.http.context import HandoverHTTPContext


def register(router: APIRouter, ctx: HandoverHTTPContext):
    store = ctx.repository_factory

    @router.post("/debug-issues", status_code=201)
    async def create_debug_issue(body: DebugWrite, request: Request):
        return await asyncio.to_thread(DebugIssues(store()).save, body, identity(request)["user"])

    @router.patch("/debug-issues/{identifier}")
    async def update_debug_issue(identifier: str, body: DebugWrite, request: Request):
        if body.version is None:
            raise ValueError("请读取记录当前版本后再保存")
        return await asyncio.to_thread(
            DebugIssues(store()).save,
            body,
            identity(request)["user"],
            identifier,
        )
