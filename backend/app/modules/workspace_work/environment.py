"""工作目录与命令白名单配置；普通对话不能提交执行命令。"""

import json
import os
from pathlib import Path
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.infrastructure.storage.files import digest
from app.modules.workspace_work.paths import workspace_root

_lock = RLock()

DEFAULT_COMMANDS = [
    ["dotnet", "build"],
    ["dotnet", "test"],
    ["dotnet", "run"],
    ["dotnet", "publish"],
    ["dotnet", "restore"],
    ["msbuild"],
    ["npm", "test"],
    ["npm", "run"],
    ["npm", "ci"],
    ["node"],
    ["python"],
    ["pytest"],
    ["git", "status"],
    ["git", "diff"],
    ["git", "log"],
    ["git", "show"],
    ["git", "branch"],
]


class WorkspaceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root: str = Field(default="", max_length=1024)
    auto_approve: bool = False
    approval_timeout_seconds: int = Field(default=120, ge=30, le=900)
    command_timeout_seconds: int = Field(default=300, ge=10, le=1800)
    commands: list[list[str]] = Field(
        default_factory=lambda: [list(row) for row in DEFAULT_COMMANDS]
    )
    version: str = ""

    @field_validator("commands")
    @classmethod
    def valid_commands(cls, value):
        for row in value:
            if (
                not isinstance(row, list)
                or not 1 <= len(row) <= 6
                or any(not isinstance(item, str) or not item or len(item) > 120 for item in row)
            ):
                raise ValueError("命令白名单必须是非空参数数组")
        return value


class WorkspaceEnvironment:
    def __init__(self, data):
        self.path = Path(data) / "workspace-work.local.json"

    def _read(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def version(self):
        return digest(self.path.read_bytes()) if self.path.exists() else ""

    def load(self, project_id):
        value = self._read().get("projects", {}).get(project_id, {})
        return WorkspaceSettings.model_validate(value)

    def public(self, project_id):
        return {
            **self.load(project_id).model_dump(),
            "version": self.version(),
            "windows": os.name == "nt",
        }

    def save(self, project_id, body, data_dir):
        with _lock:
            if body.version != self.version():
                raise ValueError("工作目录配置已更新，请刷新后重试")
            value = body.model_dump(exclude={"version"})
            if value["root"]:
                root = workspace_root(value["root"])
                data = Path(data_dir).resolve()
                if root.is_relative_to(data) or data.is_relative_to(root):
                    raise ValueError("工作目录不能与助手数据目录互相包含")
                value["root"] = str(root)
            store = self._read()
            projects = store.setdefault("projects", {})
            projects[project_id] = value
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, self.path)
            return {
                **WorkspaceSettings.model_validate(value).model_dump(),
                "version": self.version(),
                "windows": os.name == "nt",
            }
