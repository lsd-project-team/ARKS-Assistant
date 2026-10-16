"""备份导出、隔离校验和空间统计；运行中的服务不执行覆盖恢复。"""

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from app.infrastructure.database.storage import storage_stats
from app.infrastructure.storage.backup import create_backup
from app.infrastructure.storage.manifest import MAX_ARCHIVE_BYTES
from app.infrastructure.storage.validation import validate_backup
from app.modules.chat.models import Run
from app.modules.code_changes.models import CodeChangeRecord
from app.modules.source_analysis.reading.models import ProjectReadingJob


def create_router(services) -> APIRouter:
    router = APIRouter()

    def consistent_backup():
        with services.repository.lock, services.memories.lock:
            with services.database.session() as session:
                if session.query(Run).filter(Run.status.in_(("running", "queued"))).first():
                    raise ValueError("请等待当前回复完成或停止后导出备份")
                if (
                    session.query(ProjectReadingJob).filter_by(status="running").first()
                    or session.query(CodeChangeRecord).filter_by(status="verifying").first()
                ):
                    raise ValueError("请先暂停项目阅读或取消验证，再导出一致的备份")
            return create_backup(services.paths)

    @router.post("/api/backup")
    async def backup():
        async with services.runs.edit_lock:
            file = await asyncio.to_thread(consistent_backup)
        return FileResponse(file, filename=file.name, media_type="application/zip")

    @router.get("/api/storage")
    async def storage():
        return await asyncio.to_thread(storage_stats, services.paths)

    @router.post("/api/backup/validate")
    async def validate(request: Request):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "backup.zip"
            size = 0
            with file.open("wb") as outgoing:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > MAX_ARCHIVE_BYTES:
                        raise ValueError("备份 ZIP 超过 512 MiB 上限")
                    await asyncio.to_thread(outgoing.write, chunk)
            return await asyncio.to_thread(validate_backup, file)

    return router
