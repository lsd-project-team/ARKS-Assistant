"""集中装配依赖；路由接收服务对象，避免复制配置与存储逻辑。"""

from dataclasses import dataclass

from app.config import Paths, SettingsStore
from app.database import Database
from app.memory import MemoryService
from app.repository import Repository
from app.runs import RunManager
from app.runtime import AgentRuntime
from app.workspace import Workspace


@dataclass(slots=True)
class AppServices:
    paths: Paths
    settings: SettingsStore
    database: Database
    workspace: Workspace
    repository: Repository
    memories: MemoryService
    runtime: AgentRuntime
    runs: RunManager


def create_services(paths: Paths) -> AppServices:
    settings = SettingsStore(paths)
    database = Database(paths.data / "app.sqlite3")
    workspace = Workspace(paths.workspace)
    repository = Repository(database, workspace.id)
    memories = MemoryService(paths, database, workspace)
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    runs = RunManager(repository, runtime, settings)
    return AppServices(paths, settings, database, workspace, repository, memories, runtime, runs)
