"""模型、MCP、长期记忆及备份 API。"""

import asyncio

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from app.backup import create_backup
from app.config import AppSettings
from app.mcp_client import probe_mcp
from app.provider import probe_model, safe_error
from app.schemas import MemoryWrite, SettingsWrite
from app.services import AppServices


def create_router(services: AppServices) -> APIRouter:
    router = APIRouter()
    paths = services.paths
    settings = services.settings
    memories = services.memories
    runtime = services.runtime

    @router.get("/api/settings")
    async def get_settings():
        return settings.public()

    @router.put("/api/settings")
    async def save_settings(body: SettingsWrite):
        config = AppSettings.model_validate(body.settings)
        settings.preserve_mcp_secrets(config)
        settings.save(config, body.clear_api_key)
        runtime.mcp_cache.clear()
        return settings.public()

    @router.post("/api/settings/probe")
    async def test_model():
        config = settings.load()
        try:
            return await probe_model(config.model)
        except Exception as error:
            return JSONResponse({"detail": safe_error(error, config.model)}, status_code=502)

    @router.post("/api/mcp/{server_id}/probe")
    async def test_mcp(server_id: str):
        config = settings.load()
        server = next((server for server in config.mcp_servers if server.id == server_id), None)
        if not server:
            raise FileNotFoundError("MCP 配置不存在")
        try:
            return await probe_mcp(server)
        except Exception:
            return JSONResponse({"detail": "MCP 连接失败，请检查地址和连接方式"}, status_code=502)

    @router.get("/api/memories")
    async def list_memories():
        return await asyncio.to_thread(memories.list)

    @router.put("/api/memories")
    async def write_memory(body: MemoryWrite):
        return await asyncio.to_thread(memories.save, body)

    @router.delete("/api/memories/{scope}/{name}")
    async def delete_memory(scope: str, name: str, version: str):
        await asyncio.to_thread(memories.delete, scope, name, version)
        return {"ok": True}

    @router.post("/api/backup")
    async def backup():
        file = await asyncio.to_thread(create_backup, paths)
        return FileResponse(file, filename=file.name, media_type="application/zip")

    return router
