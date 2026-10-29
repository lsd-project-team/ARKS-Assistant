"""项目知识来源与记忆 API，统一通过 /api/p/{project_id} 装配。"""

import asyncio

from fastapi import APIRouter

from app.agents.runtime.model_budget import ProjectModelBudget
from app.core.container import AppServices
from app.infrastructure.providers.models import close_models, create_model
from app.modules.chat.schemas import MemoryRestore, MemoryWrite, SourcePreferencesWrite


def create_router(services: AppServices) -> APIRouter:
    router = APIRouter()
    memories = services.memories

    @router.get("/api/source-options")
    async def get_source_options():
        return services.repository.source_preferences.get()

    @router.put("/api/source-options")
    async def save_source_options(body: SourcePreferencesWrite):
        async with services.runs.edit_lock:
            return services.repository.source_preferences.save(body)

    @router.get("/api/memories")
    async def list_memories(include_deleted: bool = False):
        return await asyncio.to_thread(memories.list, include_deleted)

    @router.post("/api/memories/review")
    async def review_memory(body: MemoryWrite):
        config = services.settings.load().model
        model = (
            create_model(config) if config.model and config.base_url and config.api_key else None
        )
        if model is not None and services.repository.project_id:
            model.callbacks = [
                *(getattr(model, "callbacks", None) or []),
                ProjectModelBudget(
                    services.runtime.model_ledger,
                    config.context_tokens,
                    output_tokens=config.output_tokens,
                ),
            ]
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
