"""项目阅读 HTTP；项目访问权限由既有项目分派和认证中间件保护。"""

import asyncio

from fastapi import APIRouter

from app.core.container import AppServices
from app.modules.source_analysis.reading.schemas import ReadingCreate, ReadingReview, ReadingStart


def create_router(services: AppServices) -> APIRouter:
    router = APIRouter()
    reading = services.runtime.project_reading

    @router.get("/api/project-reading")
    async def list_jobs():
        return await asyncio.to_thread(reading.list)

    @router.post("/api/project-reading")
    async def create_job(body: ReadingCreate):
        async with services.runs.edit_lock:
            await asyncio.to_thread(services.repository.creation_guard)
            return await asyncio.to_thread(reading.create, body.title)

    @router.get("/api/project-reading/{identifier}")
    async def get_job(identifier: str):
        return await asyncio.to_thread(reading.get, identifier)

    @router.post("/api/project-reading/{identifier}/start")
    async def start_job(identifier: str, body: ReadingStart | None = None):
        async with services.runs.edit_lock:
            await asyncio.to_thread(services.repository.creation_guard)
            return await reading.start(identifier, max_chunks=(body or ReadingStart()).max_chunks)

    @router.post("/api/project-reading/{identifier}/pause")
    async def pause_job(identifier: str):
        return await reading.pause(identifier)

    @router.post("/api/project-reading/{identifier}/refresh")
    async def refresh_job(identifier: str):
        async with services.runs.edit_lock:
            await asyncio.to_thread(services.repository.creation_guard)
            return await asyncio.to_thread(reading.refresh, identifier)

    @router.get("/api/project-reading/{identifier}/files")
    async def get_files(identifier: str):
        return {"files": await asyncio.to_thread(reading.files, identifier)}

    @router.get("/api/project-reading/{identifier}/documents")
    async def get_documents(identifier: str):
        return {"documents": await asyncio.to_thread(reading.documents, identifier)}

    @router.post("/api/project-reading/{identifier}/documents/{document_id}/review")
    async def review_document(identifier: str, document_id: str, body: ReadingReview):
        async with services.runs.edit_lock:
            await asyncio.to_thread(services.repository.creation_guard)
            return await asyncio.to_thread(
                reading.review, identifier, document_id, body.version, body.decision
            )

    return router
