"""本机 API 与静态前端入口；业务逻辑放在独立服务。"""

import asyncio
import logging
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.backup import create_backup
from app.config import PROJECT_ROOT, AppSettings, Paths, SettingsStore, dump_json
from app.database import Database
from app.mcp_client import probe_mcp
from app.memory import MemoryService
from app.provider import probe_model, safe_error
from app.repository import Repository
from app.runs import RunManager
from app.runtime import AgentRuntime
from app.schemas import MemoryWrite, RunCreate, SettingsWrite, ThreadCreate, ThreadUpdate
from app.workspace import Workspace


def create_app(paths: Paths | None = None) -> FastAPI:
    paths = paths or Paths()
    settings = SettingsStore(paths)
    database = Database(paths.data / "app.sqlite3")
    workspace = Workspace(paths.workspace)
    repository = Repository(database, workspace.id)
    memories = MemoryService(paths, database, workspace)
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    runs = RunManager(repository, runtime, settings)

    @asynccontextmanager
    async def lifespan(_app):
        migration = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
        migration.attributes["connection"] = database.engine
        command.upgrade(migration, "head")
        repository.recover()
        yield
        await runs.shutdown()
        database.close()

    app = FastAPI(title="Trunk Agent", lifespan=lifespan)
    app.state.runs = runs
    app.state.repository = repository

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin:
            from urllib.parse import urlparse

            if urlparse(origin).hostname not in {"localhost", "127.0.0.1", "::1"}:
                return JSONResponse({"detail": "仅允许本机页面访问"}, status_code=403)
        return await call_next(request)

    @app.exception_handler(ValueError)
    async def invalid_request(_request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.exception_handler(ValidationError)
    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, error):
        # 不返回 Pydantic 的 input 字段，配置验证错误也不能回显刚输入的密钥。
        detail = "; ".join(
            f"{'.'.join(map(str, row['loc']))}: {row['msg']}" for row in error.errors()
        )
        return JSONResponse({"detail": detail}, status_code=422)

    @app.exception_handler(FileNotFoundError)
    async def not_found(_request, error):
        return JSONResponse({"detail": str(error)}, status_code=404)

    @app.get("/api/health")
    async def health():
        return {"ok": True, "workspace": str(paths.workspace), "workspace_id": workspace.id}

    @app.get("/api/files")
    async def files(path: str = "", query: str = ""):
        if query:
            return await asyncio.to_thread(workspace.find_files, query)
        return await asyncio.to_thread(workspace.tree, path)

    @app.get("/api/file")
    async def file(path: str):
        return await asyncio.to_thread(workspace.read, path)

    @app.get("/api/symbols")
    async def symbols(path: str):
        return await asyncio.to_thread(workspace.symbols, path)

    @app.get("/api/search")
    async def search(query: str, glob: str = "*"):
        return await asyncio.to_thread(workspace.search, query, glob)

    @app.get("/api/threads")
    async def threads():
        return repository.threads()

    @app.post("/api/threads", status_code=201)
    async def new_thread(body: ThreadCreate):
        return repository.create_thread(body.title)

    @app.get("/api/threads/{thread_id}")
    async def thread(thread_id: str):
        return repository.thread(thread_id)

    @app.patch("/api/threads/{thread_id}")
    async def rename(thread_id: str, body: ThreadUpdate):
        repository.rename(thread_id, body.title)
        return {"ok": True}

    @app.post("/api/threads/{thread_id}/runs", status_code=201)
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

    @app.get("/api/runs/{run_id}")
    async def run(run_id: str):
        return repository.run(run_id)

    @app.post("/api/runs/{run_id}/cancel")
    async def cancel(run_id: str):
        await runs.cancel(run_id)
        return repository.run(run_id)

    @app.post("/api/runs/{run_id}/resume", status_code=201)
    async def resume(run_id: str):
        run = repository.resume(run_id)
        runs.start(run)
        return run

    @app.post("/api/threads/{thread_id}/compact", status_code=201)
    async def compact(thread_id: str):
        run = repository.create_run(
            thread_id,
            "请调用 compact_conversation 压缩当前对话上下文，保留目标、结论和待办。"
            "如果尚未达到压缩条件请直接说明，无需重复之前的回答。",
            [],
        )
        runs.start(run)
        return run

    @app.get("/api/runs/{run_id}/trace")
    async def trace(run_id: str):
        rows = []
        cursor = 0
        while True:
            events = repository.events(run_id, cursor)
            rows.extend(row for row in events if row["kind"] != "token")
            if len(events) < 500:
                return rows
            cursor = events[-1]["sequence"]

    @app.get("/api/runs/{run_id}/events")
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

    @app.get("/api/settings")
    async def get_settings():
        return settings.public()

    @app.put("/api/settings")
    async def save_settings(body: SettingsWrite):
        config = AppSettings.model_validate(body.settings)
        settings.preserve_mcp_secrets(config)
        settings.save(config, body.clear_api_key)
        runtime.mcp_cache.clear()
        return settings.public()

    @app.post("/api/settings/probe")
    async def test_model():
        config = settings.load()
        try:
            return await probe_model(config.model)
        except Exception as error:
            return JSONResponse({"detail": safe_error(error, config.model)}, status_code=502)

    @app.post("/api/mcp/{server_id}/probe")
    async def test_mcp(server_id: str):
        config = settings.load()
        server = next((server for server in config.mcp_servers if server.id == server_id), None)
        if not server:
            raise FileNotFoundError("MCP 配置不存在")
        try:
            return await probe_mcp(server)
        except Exception:
            return JSONResponse({"detail": "MCP 连接失败，请检查地址和连接方式"}, status_code=502)

    @app.get("/api/memories")
    async def list_memories():
        return await asyncio.to_thread(memories.list)

    @app.put("/api/memories")
    async def write_memory(body: MemoryWrite):
        return await asyncio.to_thread(memories.save, body)

    @app.delete("/api/memories/{scope}/{name}")
    async def delete_memory(scope: str, name: str, version: str):
        await asyncio.to_thread(memories.delete, scope, name, version)
        return {"ok": True}

    @app.post("/api/backup")
    async def backup():
        file = await asyncio.to_thread(create_backup, paths)
        return FileResponse(file, filename=file.name, media_type="application/zip")

    frontend = PROJECT_ROOT / "frontend/dist"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx2").setLevel(logging.WARNING)
app = create_app()
