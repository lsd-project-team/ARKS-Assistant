"""模型、MCP、长期记忆及备份 API。"""

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import AppSettings, McpSettings
from app.mcp_client import probe_mcp
from app.model_probe import probe_capabilities
from app.provider import close_models, create_model
from app.run_feedback import error_feedback
from app.schemas import (
    McpProbe,
    MemoryRestore,
    MemoryWrite,
    ModelProbe,
    SettingsWrite,
    SourcePreferencesWrite,
)
from app.services import AppServices


def create_router(services: AppServices) -> APIRouter:
    router = APIRouter()
    settings = services.settings
    memories = services.memories
    runtime = services.runtime

    @router.get("/api/source-options")
    async def get_source_options():
        return services.repository.source_preferences.get()

    @router.put("/api/source-options")
    async def save_source_options(body: SourcePreferencesWrite):
        async with services.runs.edit_lock:
            return services.repository.source_preferences.save(body)

    @router.get("/api/settings")
    async def get_settings():
        return settings.public()

    @router.put("/api/settings")
    async def save_settings(body: SettingsWrite):
        config = AppSettings.model_validate(body.settings)
        settings.save(
            config, body.clear_api_key, clear_keys=body.clear_profile_keys, version=body.version
        )
        runtime.mcp_cache.clear()
        return settings.public()

    @router.post("/api/settings/probe")
    async def test_model(body: ModelProbe | None = None):
        config = (
            settings.prepare(
                AppSettings.model_validate(body.settings), body.clear_profile_keys, body.version
            )
            if body and body.settings
            else settings.load()
        )
        selected_id = body.profile_id if body and body.profile_id else config.active_profile_id
        profile = next((item for item in config.model_profiles if item.id == selected_id), None)
        if not profile:
            raise FileNotFoundError("模型配置不存在")
        try:
            result = await probe_capabilities(profile.config)
            settings.record_probe(profile.id, profile.config, result)
            return {"profile_id": profile.id, **result}
        except Exception as error:
            feedback = error_feedback(error, profile.config)
            return JSONResponse({"detail": feedback["text"], **feedback}, status_code=502)

    @router.post("/api/mcp/{server_id}/probe")
    async def test_mcp(server_id: str, body: McpProbe | None = None):
        config = settings.load()
        server = (
            settings.prepare_server(McpSettings.model_validate(body.server))
            if body and body.server
            else next((server for server in config.mcp_servers if server.id == server_id), None)
        )
        if not server:
            raise FileNotFoundError("MCP 配置不存在")
        if server.id != server_id:
            raise ValueError("待测试 MCP ID 与请求不一致")
        try:
            return await probe_mcp(server)
        except Exception:
            return JSONResponse({"detail": "MCP 连接失败，请检查地址和连接方式"}, status_code=502)

    @router.get("/api/memories")
    async def list_memories(include_deleted: bool = False):
        return await asyncio.to_thread(memories.list, include_deleted)

    @router.post("/api/memories/review")
    async def review_memory(body: MemoryWrite):
        config = settings.load().model
        model = (
            create_model(config) if config.model and config.base_url and config.api_key else None
        )
        try:
            return await memories.semantic_review(body, model)
        finally:
            await close_models([model] if model else [])

    @router.get("/api/memories/{scope}/{name}/history")
    async def memory_history(scope: str, name: str):
        MemoryWrite(name=name, scope=scope, content="")
        return await asyncio.to_thread(memories.history.list, scope, name)

    @router.post("/api/memories/{scope}/{name}/restore")
    async def restore_memory(scope: str, name: str, body: MemoryRestore):
        return await asyncio.to_thread(memories.restore, scope, name, body)

    @router.put("/api/memories")
    async def write_memory(body: MemoryWrite):
        return await asyncio.to_thread(memories.save, body)

    @router.delete("/api/memories/{scope}/{name}")
    async def delete_memory(scope: str, name: str, version: str):
        await asyncio.to_thread(memories.delete, scope, name, version)
        return {"ok": True}

    return router
