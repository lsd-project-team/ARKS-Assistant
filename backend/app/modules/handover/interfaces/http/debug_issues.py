"""交接工作台 debug_issues 接口。"""

import asyncio

from fastapi import APIRouter, Query, Request, Response

from app.modules.auth.router import identity
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.domain.images import MAX_IMAGE_BYTES
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

    @router.post("/debug-issues/{identifier}/images", status_code=201)
    async def add_image(
        identifier: str,
        request: Request,
        version: int = Query(ge=1),
        filename: str = Query(min_length=1, max_length=250),
        recorded_at: str = Query(default="", max_length=2000),
    ):
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError("每张原图不能超过 8 MB")
        return await asyncio.to_thread(
            DebugIssues(store()).add_image,
            identifier,
            version,
            bytes(data),
            filename,
            recorded_at,
            identity(request)["user"],
        )

    @router.get("/debug-issues/{identifier}/images/{version}/{index}")
    async def image(identifier: str, version: int, index: int):
        blob = await asyncio.to_thread(store().debug_image, identifier, version, index)
        return Response(
            blob["content"],
            media_type=blob["media_type"],
            headers={"X-Content-Type-Options": "nosniff"},
        )
