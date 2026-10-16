"""本机 API 与静态前端入口；业务逻辑放在独立服务。"""

import asyncio
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.agents.runtime.engine import AgentRuntime
from app.core import health as health
from app.core.config import PROJECT_ROOT, Paths, SettingsStore
from app.core.container import AppServices
from app.core.process_lock import service_lock
from app.infrastructure.database.session import Database
from app.modules.admin.router import create_router as admin_router
from app.modules.admin.router import usage_router
from app.modules.admin.tracking import UsageTracking
from app.modules.auth.middleware import install_authentication
from app.modules.auth.router import create_router as auth_router
from app.modules.auth.service import AuthService
from app.modules.chat.repository import Repository
from app.modules.chat.runs import RunManager
from app.modules.handover.infrastructure.exporters.archive import DocumentPackageExporter
from app.modules.handover.infrastructure.parsers.documents import DocumentParser
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.handover.interfaces.http.router import create_router as handover_router
from app.modules.memory.service import MemoryService
from app.modules.projects.router import ProjectDispatcher
from app.modules.projects.router import create_router as projects_router
from app.modules.projects.service import Projects
from app.modules.settings import data_router as data
from app.modules.settings import router as configuration
from app.modules.source_analysis.workspace import Workspace


def create_app(paths: Paths | None = None) -> FastAPI:
    paths = paths or Paths()
    if (paths.data / "restore.pending.json").exists():
        raise RuntimeError("检测到未完成的数据恢复，请先运行恢复工具的 --rollback，再启动服务")
    services = create_services(paths)
    projects = Projects(services)

    def handover_store():
        return HandoverStore(projects)

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
                services.runtime.project_reading.recover(all_projects=True)
                services.runtime.code_changes.recover(all_projects=True)
                await asyncio.to_thread(services.runtime.code_changes.cleanup_executors)
                yield
            finally:
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
    app.include_router(
        handover_router(projects, handover_store, DocumentParser(), DocumentPackageExporter())
    )
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


def create_services(paths: Paths) -> AppServices:
    settings = SettingsStore(paths)
    database = Database(paths.data / "app.sqlite3")
    workspace = Workspace(paths.workspace)
    repository = Repository(database, workspace.id)
    memories = MemoryService(paths, database, workspace)
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    runs = RunManager(repository, runtime, settings)
    runtime.project_lock = runs.edit_lock
    return AppServices(paths, settings, database, workspace, repository, memories, runtime, runs)
