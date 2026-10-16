"""分支、问题编辑与等待队列的 API，所有变更共享运行编辑锁。"""

from fastapi import APIRouter

from app.core.container import AppServices
from app.modules.chat.schemas import BranchCreate, QueueEdit, RunCreate


def validated_selections(workspace, body):
    selections = []
    for selection in body.selections:
        if selection.source_workspace_id and selection.source_workspace_id != workspace.source_id:
            raise ValueError("选区来自其他源码目录，请在当前项目重新选择；原始快照仍保留")
        workspace.resolve(selection.path)
        try:
            stale = workspace.read(selection.path)["version"] != selection.version
        except FileNotFoundError:
            stale = True
        selections.append(
            {**selection.model_dump(), "source_workspace_id": workspace.source_id, "stale": stale}
        )
    return selections


def source_options(body):
    return body.source_options.model_dump() if body.source_options is not None else None


def create_router(services: AppServices):
    router = APIRouter()
    repository, manager = services.repository, services.runs

    @router.post("/api/threads/{thread_id}/fork", status_code=201)
    async def fork(thread_id: str, body: BranchCreate):
        async with manager.edit_lock:
            return repository.branches.fork(thread_id, body.message_id)

    @router.post("/api/threads/{thread_id}/messages/{message_id}/edit", status_code=201)
    async def edit(thread_id: str, message_id: str, body: RunCreate):
        selections = validated_selections(services.workspace, body)
        async with manager.edit_lock:
            run = repository.branches.edit_latest(
                thread_id, message_id, body.content, selections, source_options(body)
            )
            manager.start(run)
        return run

    @router.get("/api/threads/{thread_id}/queue")
    async def queue(thread_id: str):
        return repository.queue.list(thread_id)

    @router.post("/api/threads/{thread_id}/queue", status_code=201)
    async def enqueue(thread_id: str, body: RunCreate):
        selections = validated_selections(services.workspace, body)
        async with manager.edit_lock:
            item = repository.queue.add(thread_id, body.content, selections, source_options(body))
            run = repository.queue.dispatch(thread_id)
            if run:
                manager.start(run)
        return {"item": item, "started_run": run}

    @router.patch("/api/queue/{item_id}")
    async def update(item_id: str, body: QueueEdit):
        selections = validated_selections(services.workspace, body)
        async with manager.edit_lock:
            return repository.queue.update(
                item_id, body.content, selections, body.version, source_options(body)
            )

    @router.delete("/api/queue/{item_id}")
    async def remove(item_id: str):
        async with manager.edit_lock:
            repository.queue.cancel(item_id)
        return {"ok": True}

    @router.post("/api/threads/{thread_id}/queue/{action}")
    async def control_queue(thread_id: str, action: str):
        if action not in {"pause", "continue"}:
            raise ValueError("队列操作必须是 pause 或 continue")
        async with manager.edit_lock:
            thread = repository.catalog.get(thread_id)
            if action == "continue" and thread["state"] == "archived":
                repository.catalog.change(thread_id, "active")
            repository.queue.pause(thread_id, action == "pause")
            run = repository.queue.dispatch(thread_id)
            if run:
                manager.start(run)
        return {"started_run": run, **repository.queue.list(thread_id)}

    return router
