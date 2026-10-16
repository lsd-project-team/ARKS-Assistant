"""HTTP 依赖容器，仅保存由应用入口注入的服务与仓储工厂。"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.modules.handover.application.ports import MaterialParser, PackageExporter, RecordRepository


@dataclass(frozen=True, slots=True)
class HandoverHTTPContext:
    projects: Any
    ai: Any
    repository_factory: Callable[[], RecordRepository]
    parser: MaterialParser
    exporter: PackageExporter

    def source_workspace(self, project_id):
        return (
            self.projects.services(project_id).workspace
            if project_id
            else self.projects.base.workspace
        )
