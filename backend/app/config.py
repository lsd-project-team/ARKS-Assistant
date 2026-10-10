"""路径配置与供应商配置；密钥只保存在本机，API 返回值始终脱敏。"""

import json
import os
from pathlib import Path
from threading import RLock
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ModelSettings(BaseModel):
    protocol: Literal["openai", "anthropic"] = "openai"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    context_tokens: int = Field(default=32768, ge=2048, le=2_000_000)
    output_tokens: int = Field(default=4096, ge=256, le=65536)
    temperature: float = Field(default=0.2, ge=0, le=2)
    timeout_seconds: int = Field(default=120, ge=10, le=600)
    summary_model: str = ""

    @model_validator(mode="after")
    def validate_budget(self):
        if self.output_tokens >= self.context_tokens - 1024:
            raise ValueError("回复 token 上限必须为输入上下文预留至少 1024 token")
        return self

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("接口地址必须以 http:// 或 https:// 开头")
        return value


class McpSettings(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    name: str = Field(min_length=1, max_length=80)
    enabled: bool = True
    transport: Literal["streamable_http", "sse", "stdio"] = "streamable_http"
    url: str = ""
    command: str = ""
    args: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    env: dict[str, str] = Field(default_factory=dict)


class AppSettings(BaseModel):
    model: ModelSettings = Field(default_factory=ModelSettings)
    mcp_servers: list[McpSettings] = Field(default_factory=list)
    auto_memory: bool = True
    deepwiki_repo: str = ""


class Paths:
    def __init__(self, data_dir: Path | None = None, workspace: Path | None = None):
        self.data = data_dir or Path(os.getenv("TRUNK_AGENT_DATA_DIR", PROJECT_ROOT / "data"))
        self.workspace = workspace or Path(
            os.getenv("TRUNK_AGENT_WORKSPACE", PROJECT_ROOT / "trunk")
        )
        self.data = self.data.resolve()
        self.workspace = self.workspace.resolve()
        self.memories = self.data / "memories"
        self.scratch = self.data / "scratch"
        for directory in (self.data, self.memories, self.scratch):
            directory.mkdir(parents=True, exist_ok=True)


class SettingsStore:
    def __init__(self, paths: Paths):
        self.path = paths.data / "settings.private.json"
        self._lock = RLock()

    def load(self) -> AppSettings:
        with self._lock:
            if not self.path.exists():
                return AppSettings()
            return AppSettings.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, settings: AppSettings, clear_key: bool = False) -> None:
        with self._lock:
            if not settings.model.api_key and not clear_key:
                settings.model.api_key = self.load().model.api_key
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(self.path)

    def public(self) -> dict:
        settings = self.load()
        result = settings.model_dump()
        result["model"]["has_api_key"] = bool(settings.model.api_key)
        result["model"]["api_key"] = ""
        for server in result["mcp_servers"]:
            server["headers"] = {key: "••••••" for key in server["headers"]}
            server["env"] = {key: "••••••" for key in server["env"]}
        return result

    def preserve_mcp_secrets(self, settings: AppSettings) -> None:
        existing = {server.id: server for server in self.load().mcp_servers}
        for server in settings.mcp_servers:
            previous = existing.get(server.id)
            if not previous:
                continue
            for field in ("headers", "env"):
                values = getattr(server, field)
                stored = getattr(previous, field)
                for key, value in values.items():
                    if value == "••••••":
                        values[key] = stored.get(key, "")


def dump_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
