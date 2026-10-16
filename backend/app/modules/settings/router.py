"""全局模型与 MCP 配置 API，不再重复挂载到各项目。"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.agents.runtime.feedback import error_feedback
from app.core.config import AppSettings, McpSettings
from app.core.container import AppServices
from app.infrastructure.mcp.client import probe_mcp
from app.modules.chat.schemas import (
    McpProbe,
    ModelProbe,
    SettingsWrite,
)
from app.modules.settings.model_probe import probe_capabilities


def create_router(services: AppServices) -> APIRouter:
    router = APIRouter()
    settings = services.settings
    runtime = services.runtime

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

    return router
