"""空会话整理使用预览和条件更新，资料已变化时整个批次回滚。"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import and_, exists, func, or_, select, update

from app.models import MemoryRecord, Message, QueuedQuestion, Run, Thread, now_iso
from app.records import record_dict


class CleanupSelection(BaseModel):
    versions: dict[str, str] = Field(min_length=1, max_length=200)


class EmptyConversations:
    def __init__(self, repository):
        self.repository = repository

    def eligibility(self):
        return [
            Thread.workspace_id == self.repository.workspace_id,
            Thread.state == "active",
            Thread.pinned_order.is_(None),
            *[
                ~exists(select(model.id).where(model.thread_id == Thread.id))
                for model in (Message, Run, QueuedQuestion)
            ],
            ~exists(select(MemoryRecord.id).where(MemoryRecord.source_thread_id == Thread.id)),
        ]

    def preview(self):
        with self.repository.database.session() as session:
            rows = session.scalars(
                select(Thread).where(*self.eligibility()).order_by(Thread.created_at).limit(200)
            )
            return {
                "threads": [record_dict(row) for row in rows],
                "total": session.scalar(select(func.count(Thread.id)).where(*self.eligibility())),
            }

    def change(self, versions: dict[str, str], *, restore=False):
        version = now_iso()
        predicate = (
            [Thread.workspace_id == self.repository.workspace_id, Thread.state == "deleted"]
            if restore
            else self.eligibility()
        )
        compared = Thread.deleted_at if restore else Thread.updated_at
        predicate.append(
            or_(*[and_(Thread.id == key, compared == value) for key, value in versions.items()])
        )
        with self.repository.lock, self.repository.database.session.begin() as session:
            result = session.execute(
                update(Thread)
                .where(*predicate)
                .values(
                    state="active" if restore else "deleted",
                    deleted_at=None if restore else version,
                    updated_at=version,
                    queue_paused=True,
                )
            )
            # 条件直接参与 UPDATE；预览后产生消息、改名或置顶都不能误删，部分命中也回滚。
            if result.rowcount != len(versions):
                raise ValueError("会话列表已变化，本次没有整理任何对话，请重新加载预览")
        return {"ids": list(versions), "version": version}


def create_router(services):
    router = APIRouter()
    cleanup = EmptyConversations(services.repository)

    @router.get("/api/threads/empty")
    async def preview():
        return cleanup.preview()

    @router.post("/api/threads/empty/trash")
    async def trash(body: CleanupSelection):
        async with services.runs.edit_lock:
            return cleanup.change(body.versions)

    @router.post("/api/threads/empty/restore")
    async def restore(body: CleanupSelection):
        async with services.runs.edit_lock:
            return cleanup.change(body.versions, restore=True)

    return router
