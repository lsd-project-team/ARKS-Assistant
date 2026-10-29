"""后台记忆只读接口；来源选择继续复用项目设置。"""

import asyncio

from fastapi import APIRouter
from sqlalchemy import select

from app.core.container import AppServices
from app.modules.chat.schemas import SourcePreferencesWrite
from app.modules.memory.identity import user_memory_owner
from app.modules.memory.models import MemoryExtraction


def create_router(services: AppServices) -> APIRouter:
    router = APIRouter()

    @router.get("/api/source-options")
    async def get_source_options():
        return services.repository.source_preferences.get()

    @router.put("/api/source-options")
    async def save_source_options(body: SourcePreferencesWrite):
        async with services.runs.edit_lock:
            return services.repository.source_preferences.save(body)

    @router.get("/api/memories")
    async def list_memories():
        return await asyncio.to_thread(services.memories.list)

    @router.get("/api/memories/status")
    async def memory_status():
        config = services.settings.load()
        with services.database.session() as session:
            rows = list(
                session.scalars(
                    select(MemoryExtraction).where(
                        MemoryExtraction.owner_id == (user_memory_owner() or "local"),
                        MemoryExtraction.workspace_id == services.workspace.id,
                    )
                )
            )
            return {
                "enabled": config.auto_memory,
                "idle_hours": config.memory_generation.idle_hours,
                "states": {
                    state: sum(row.state == state for row in rows)
                    for state in ("pending", "running", "extracted", "completed", "failed")
                },
                "last_error": next(
                    (row.error_code for row in reversed(rows) if row.state == "failed"), ""
                ),
            }

    return router
