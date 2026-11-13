"""流式接收原文件，上传和解析不阻塞聊天事件循环。"""

import asyncio

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from app.modules.chat.attachment_parsing import MAX_UPLOAD, filename_for


def create_router(services):
    router = APIRouter()
    store = services.repository.attachments

    @router.post("/api/attachments", status_code=201)
    async def upload(request: Request, filename: str = Query(min_length=1, max_length=250)):
        filename_for(filename)
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > MAX_UPLOAD:
                raise ValueError("单个文件不能超过 32 MB")
            content.extend(chunk)
        return await asyncio.to_thread(store.upload, bytes(content), filename)

    @router.get("/api/attachments/{identifier}")
    def read(
        identifier: str, offset: int = Query(0, ge=0), limit: int = Query(12000, ge=1, le=12000)
    ):
        return store.read(identifier, offset, limit)

    @router.get("/api/attachments/{identifier}/download")
    def download(identifier: str):
        path, filename = store.download(identifier)
        return FileResponse(path, filename=filename, media_type="application/octet-stream")

    @router.get("/api/attachments/{identifier}/image")
    def image(identifier: str):
        # 只对真实图片声明图片类型并允许内联显示，避免把任意附件当页面渲染。
        path, filename, media_type = store.image(identifier)
        return FileResponse(
            path, filename=filename, media_type=media_type, content_disposition_type="inline"
        )

    @router.delete("/api/attachments/{identifier}")
    async def remove(identifier: str):
        async with services.runs.edit_lock:
            store.remove(identifier)
        return {"ok": True}

    return router
