"""会话和运行 API；SSE 连接仅订阅持久化事件。"""

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response, StreamingResponse

from app.api.conversation_workflows import create_router as workflows_router
from app.api.conversation_workflows import validated_selections
from app.config import dump_json
from app.conversation_context import ConversationContext
from app.conversation_lifecycle import ConversationLifecycle
from app.memory_visibility import run_memory_actor, visible_run_event
from app.schemas import (
    PinMove,
    PinnedOrder,
    RunCreate,
    SummaryCorrection,
    ThreadCreate,
    ThreadUpdate,
)
from app.services import AppServices


def create_router(services: AppServices) -> APIRouter:
    router = APIRouter()
    router.include_router(workflows_router(services))
    workspace = services.workspace
    repository = services.repository
    runs = services.runs
    context = ConversationContext(services.runtime)
    lifecycle = ConversationLifecycle(services)

    @router.get("/api/threads")
    async def threads(
        state: str = "active",
        query: str = "",
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ):
        return repository.threads(state, query, limit, offset)

    @router.put("/api/threads/pinned-order")
    async def reorder(body: PinnedOrder):
        repository.catalog.reorder(body.ids)
        return {"ok": True}

    @router.post("/api/threads", status_code=201)
    async def new_thread(body: ThreadCreate):
        async with runs.edit_lock:
            return repository.create_thread(body.title)

    async def start_run(body: RunCreate, thread_id: str | None):
        selections = validated_selections(workspace, body)
        async with runs.edit_lock:
            options = body.source_options.model_dump() if body.source_options else None
            run = repository.create_run(thread_id, body.content, selections, options)
            runs.start(run)
        return run

    @router.post("/api/threads/start", status_code=201)
    async def first_run(body: RunCreate):
        return await start_run(body, None)

    @router.get("/api/threads/{thread_id}")
    async def thread(
        thread_id: str,
        limit: int = Query(default=80, ge=1, le=200),
        before: str | None = None,
        around: str | None = None,
    ):
        return repository.thread(thread_id, limit, before, around)

    @router.patch("/api/threads/{thread_id}")
    async def rename(thread_id: str, body: ThreadUpdate):
        async with runs.edit_lock:
            if body.title is not None:
                repository.rename(thread_id, body.title)
            if body.state is not None:
                repository.catalog.change(thread_id, body.state)
            if body.pinned is not None:
                repository.catalog.pin(thread_id, body.pinned)
        return repository.catalog.get(thread_id)

    @router.post("/api/threads/{thread_id}/read")
    async def mark_read(thread_id: str):
        repository.catalog.mark_read(thread_id)
        return {"ok": True}

    @router.post("/api/threads/{thread_id}/pin-position")
    async def move_pin(thread_id: str, body: PinMove):
        repository.catalog.move_pin(thread_id, body.direction)
        return {"ok": True}

    @router.get("/api/threads/{thread_id}/export")
    async def export(thread_id: str, format: str = "markdown"):
        data = repository.thread(thread_id)
        if format == "json":
            content = dump_json({"schema_version": 1, "conversation": data})
            extension, media_type = "json", "application/json"
        elif format == "markdown":
            rows = [f"# {data['title']}", f"导出会话：{thread_id}"]
            for message in data["messages"]:
                rows.append(f"\n## {'用户' if message['role'] == 'user' else '助手'}\n")
                rows.append(message["content"])
                for selection in message["selections"]:
                    rows.append(
                        f"\n源码快照：{selection['path']} "
                        f"L{selection['start_line']}–{selection['end_line']}\n"
                        f"\n````\n{selection['content']}\n````\n"
                    )
            content, extension, media_type = "\n\n".join(rows), "md", "text/markdown"
        else:
            raise ValueError("导出格式必须是 markdown 或 json")
        filename = f"conversation-{thread_id}.{extension}"
        return Response(
            content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.delete("/api/threads/{thread_id}")
    async def trash(thread_id: str):
        async with runs.edit_lock:
            return await lifecycle.trash(thread_id)

    @router.post("/api/threads/{thread_id}/restore")
    async def restore(thread_id: str):
        async with runs.edit_lock:
            return repository.catalog.change(thread_id, "active")

    @router.delete("/api/threads/{thread_id}/permanent")
    async def purge(thread_id: str):
        async with runs.edit_lock:
            await lifecycle.purge(thread_id)
        return {"ok": True}

    @router.post("/api/threads/{thread_id}/runs", status_code=201)
    async def new_run(thread_id: str, body: RunCreate):
        return await start_run(body, thread_id)

    @router.get("/api/runs/{run_id}")
    async def run(run_id: str):
        return repository.run(run_id)

    @router.post("/api/runs/{run_id}/cancel")
    async def cancel(run_id: str):
        async with runs.edit_lock:
            await runs.cancel(run_id)
        return repository.run(run_id)

    @router.post("/api/runs/{run_id}/resume", status_code=201)
    async def resume(run_id: str):
        async with runs.edit_lock:
            run = repository.resume(run_id)
            runs.start(run)
        return run

    @router.post("/api/threads/{thread_id}/compact", status_code=201)
    async def compact(thread_id: str):
        async with runs.edit_lock:
            run = repository.create_run(
                thread_id,
                "请调用 compact_conversation 压缩当前对话上下文，保留目标、结论和待办。"
                "如果尚未达到压缩条件请直接说明，无需重复之前的回答。",
                [],
            )
            runs.start(run)
        return run

    @router.post("/api/runs/{run_id}/regenerate", status_code=201)
    async def regenerate(run_id: str):
        async with runs.edit_lock:
            run = repository.regenerate(run_id)
            runs.start(run)
        return run

    @router.get("/api/threads/{thread_id}/context")
    async def conversation_context(thread_id: str):
        return await context.read(thread_id)

    @router.patch("/api/threads/{thread_id}/context")
    async def correct_context(thread_id: str, body: SummaryCorrection):
        async with runs.edit_lock:
            return await context.correct(thread_id, body)

    @router.get("/api/runs/{run_id}/context")
    async def run_context(run_id: str):
        return context.run_sources(run_id)

    @router.get("/api/runs/{run_id}/trace")
    async def trace(run_id: str):
        run = repository.run(run_id)
        actor_id = run_memory_actor(repository, run)
        rows = []
        cursor = 0
        while True:
            events = repository.events(run_id, cursor)
            rows.extend(
                visible
                for row in events
                if row["kind"] != "token"
                and (visible := visible_run_event(row, actor_id)) is not None
            )
            if len(events) < 500:
                return rows
            cursor = events[-1]["sequence"]

    @router.get("/api/runs/{run_id}/events")
    async def events(run_id: str, request: Request, after: int = 0):
        run = repository.run(run_id)
        actor_id = run_memory_actor(repository, run)
        cursor = max(after, int(request.headers.get("last-event-id", "0")))

        async def output():
            async for event in runs.stream(run_id, cursor):
                if await request.is_disconnected():
                    return
                event = visible_run_event(event, actor_id)
                if event is None:
                    continue
                yield (
                    f"id: {event['sequence']}\nevent: {event['kind']}\n"
                    f"data: {dump_json(event['payload'])}\n\n"
                )

        return StreamingResponse(
            output(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
