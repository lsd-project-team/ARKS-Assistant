"""本机 API 与静态前端入口；业务逻辑放在独立服务。"""

import logging
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.admin.router import create_router as admin_router
from app.admin.router import usage_router
from app.admin.tracking import UsageTracking
from app.api import configuration, data, health
from app.api.projects import ProjectDispatcher
from app.api.projects import create_router as projects_router
from app.auth.middleware import install_authentication
from app.auth.router import create_router as auth_router
from app.auth.service import AuthService
from app.config import PROJECT_ROOT, Paths
from app.handover.ai import HandoverAI
from app.handover.router import create_router as handover_router
from app.process_lock import service_lock
from app.projects import Projects
from app.services import create_services


def create_app(paths: Paths | None = None) -> FastAPI:
    paths = paths or Paths()
    if (paths.data / "restore.pending.json").exists():
        raise RuntimeError("检测到未完成的数据恢复，请先运行恢复工具的 --rollback，再启动服务")
    services = create_services(paths)
    projects = Projects(services)
    handover_ai = HandoverAI(projects)
    auth = AuthService(services.database, paths)
    usage = UsageTracking(services.database)

    @asynccontextmanager
    async def lifespan(_app):
        with service_lock(services.paths.data):
            try:
                migration = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
                migration.attributes["connection"] = services.database.engine
                command.upgrade(migration, "head")
                auth.initialize()
                usage.initialize()
                projects.initialize()
                services.repository.recover()
                handover_ai.recover()
                yield
            finally:
                await handover_ai.shutdown()
                await projects.shutdown()
                services.database.close()

    app = FastAPI(title="Trunk Agent", lifespan=lifespan)
    app.state.runs = services.runs
    app.state.repository = services.repository
    app.state.projects = projects
    app.state.auth = auth
    app.state.usage = usage
    install_authentication(app, auth, usage)
    app.include_router(auth_router(auth, projects))
    app.include_router(admin_router(auth, usage))
    app.include_router(usage_router(usage))

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

    for module in (health, configuration, data):
        app.include_router(module.create_router(services))
    app.include_router(projects_router(projects))
    app.include_router(handover_router(projects, handover_ai))
    app.mount("/api/p", ProjectDispatcher(projects, app.exception_handlers))

    @app.api_route(
        "/api/{unmatched:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]
    )
    async def unknown_api(unmatched: str):
        return JSONResponse({"detail": "接口不存在"}, status_code=404)

    frontend = PROJECT_ROOT / "frontend/dist"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx2").setLevel(logging.WARNING)
app = create_app()
