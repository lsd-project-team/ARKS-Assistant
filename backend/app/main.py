"""本机 API 与静态前端入口；业务逻辑放在独立服务。"""

import logging
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.api import configuration, conversations, data, workspace
from app.config import PROJECT_ROOT, Paths
from app.process_lock import service_lock
from app.services import create_services


def create_app(paths: Paths | None = None) -> FastAPI:
    paths = paths or Paths()
    if (paths.data / "restore.pending.json").exists():
        raise RuntimeError("检测到未完成的数据恢复，请先运行恢复工具的 --rollback，再启动服务")
    services = create_services(paths)

    @asynccontextmanager
    async def lifespan(_app):
        with service_lock(services.paths.data):
            try:
                migration = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
                migration.attributes["connection"] = services.database.engine
                command.upgrade(migration, "head")
                services.repository.recover()
                yield
            finally:
                await services.runs.shutdown()
                services.database.close()

    app = FastAPI(title="Trunk Agent", lifespan=lifespan)
    app.state.runs = services.runs
    app.state.repository = services.repository

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

    for module in (workspace, conversations, configuration, data):
        app.include_router(module.create_router(services))
    frontend = PROJECT_ROOT / "frontend/dist"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx2").setLevel(logging.WARNING)
app = create_app()
