"""会话和运行 API；SSE 连接仅订阅持久化事件。"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import dump_json
from app.schemas import RunCreate, ThreadCreate, ThreadUpdate
from app.services import AppServices


def create_router(services: AppServices) -> APIRouter:
    router = APIRouter()
    workspace = services.workspace
    repository = services.repository
    runs = services.runs

    @router.get("/api/threads")
    async def threads():
        return repository.threads()

    @router.post("/api/threads", status_code=201)
    async def new_thread(body: ThreadCreate):
        return repository.create_thread(body.title)

    @router.get("/api/threads/{thread_id}")
    async def thread(thread_id: str):
        return repository.thread(thread_id)

    @router.patch("/api/threads/{thread_id}")
    async def rename(thread_id: str, body: ThreadUpdate):
        repository.rename(thread_id, body.title)
        return {"ok": True}

    @router.post("/api/threads/{thread_id}/runs", status_code=201)
    async def new_run(thread_id: str, body: RunCreate):
        selections = []
        for selection in body.selections:
            current = workspace.read(selection.path)
            selections.append(
                {**selection.model_dump(), "stale": current["version"] != selection.version}
            )
        run = repository.create_run(thread_id, body.content, selections)
        runs.start(run)
        return run

    @router.get("/api/runs/{run_id}")
    async def run(run_id: str):
        return repository.run(run_id)

    @router.post("/api/runs/{run_id}/cancel")
    async def cancel(run_id: str):
        await runs.cancel(run_id)
        return repository.run(run_id)

    @router.post("/api/runs/{run_id}/resume", status_code=201)
    async def resume(run_id: str):
        run = repository.resume(run_id)
        runs.start(run)
        return run

    @router.post("/api/threads/{thread_id}/compact", status_code=201)
    async def compact(thread_id: str):
        run = repository.create_run(
            thread_id,
            "请调用 compact_conversation 压缩当前对话上下文，保留目标、结论和待办。"
            "如果尚未达到压缩条件请直接说明，无需重复之前的回答。",
            [],
        )
        runs.start(run)
        return run

    @router.get("/api/runs/{run_id}/trace")
    async def trace(run_id: str):
        rows = []
        cursor = 0
        while True:
            events = repository.events(run_id, cursor)
            rows.extend(row for row in events if row["kind"] != "token")
            if len(events) < 500:
                return rows
            cursor = events[-1]["sequence"]

    @router.get("/api/runs/{run_id}/events")
    async def events(run_id: str, request: Request, after: int = 0):
        repository.run(run_id)
        cursor = max(after, int(request.headers.get("last-event-id", "0")))

        async def output():
            async for event in runs.stream(run_id, cursor):
                if await request.is_disconnected():
                    return
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
