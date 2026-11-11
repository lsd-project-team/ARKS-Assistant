"""应用服务容器的类型契约；业务模块不依赖启动装配。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.runtime.engine import AgentRuntime
    from app.core.config import Paths, SettingsStore
    from app.infrastructure.database.session import Database
    from app.modules.chat.repository import Repository
    from app.modules.chat.runs import RunManager
    from app.modules.memory.service import MemoryService
    from app.modules.source_analysis.workspace import Workspace


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
