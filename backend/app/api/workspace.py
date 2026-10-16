"""工作区目录、源码、搜索与语法符号 API。"""

import asyncio

from fastapi import APIRouter

from app.services import AppServices


def create_router(services: AppServices) -> APIRouter:
    router = APIRouter()
    workspace = services.workspace

    @router.get("/api/files")
    async def files(path: str = "", query: str = ""):
        if query:
            return await asyncio.to_thread(workspace.find_files, query)
        return await asyncio.to_thread(workspace.tree, path)

    @router.get("/api/files/quick-open")
    async def quick_open(query: str = ""):
        return await asyncio.to_thread(workspace.find_files, query, 50)

    @router.get("/api/file")
    async def file(path: str):
        return await asyncio.to_thread(workspace.read, path)

    @router.get("/api/symbols")
    async def symbols(path: str):
        return await asyncio.to_thread(workspace.symbols, path)

    @router.get("/api/search")
    async def search(query: str, glob: str = "*"):
        return await asyncio.to_thread(workspace.search, query, glob)

    return router
