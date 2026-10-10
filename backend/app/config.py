"""路径配置与供应商配置；密钥只保存在本机，API 返回值始终脱敏。"""

import json
import os
import re
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SECRET_MASK = "••••••"


def http_address(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value:
        return value
    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or any(char.isspace() for char in value)
    ):
        raise ValueError("地址必须是完整的 HTTP 或 HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("请通过密钥或 headers 配置凭据，不要放在地址中")
    return value


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
        return http_address(value)


class ModelProfile(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    name: str = Field(min_length=1, max_length=80)
    config: ModelSettings = Field(default_factory=ModelSettings)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        if not value.strip():
            raise ValueError("配置名称不能为空")
        return value.strip()


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

    @field_validator("headers", "env")
    @classmethod
    def validate_credentials(cls, values, info):
        pattern = (
            r"[A-Za-z_][A-Za-z0-9_]*"
            if info.field_name == "env"
            else r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
        )
        if any(not re.fullmatch(pattern, key) for key in values):
            raise ValueError("环境变量或请求头名称无效")
        if info.field_name == "headers" and any(
            "\r" in value or "\n" in value for value in values.values()
        ):
            raise ValueError("请求头值不能包含换行")
        return values

    @model_validator(mode="after")
    def validate_connection(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("MCP 名称不能为空")
        self.url = http_address(self.url)
        if self.enabled and self.transport == "stdio" and not self.command.strip():
            raise ValueError("本地 MCP 命令不能为空")
        if self.enabled and self.transport != "stdio" and not self.url:
            raise ValueError("HTTP MCP 地址不能为空")
        return self


class AppSettings(BaseModel):
    model: ModelSettings = Field(default_factory=ModelSettings)
    model_profiles: list[ModelProfile] = Field(default_factory=list, max_length=20)
    active_profile_id: str = ""
    mcp_servers: list[McpSettings] = Field(default_factory=list, max_length=20)
    auto_memory: bool = True
    deepwiki_repo: str = ""

    @model_validator(mode="before")
    @classmethod
    def legacy_model_override(cls, value):
        if not isinstance(value, dict) or "model" not in value or not value.get("model_profiles"):
            return value
        if not isinstance(value["model_profiles"], list) or any(
            not isinstance(profile, dict) for profile in value["model_profiles"]
        ):
            return value
        selected = value.get("active_profile_id") or value["model_profiles"][0].get("id")
        # 旧客户端仍通过 model 修改当前配置；新客户端写入时省略这个兼容字段。
        profiles = [
            {**profile, "config": value["model"]} if profile.get("id") == selected else profile
            for profile in value["model_profiles"]
        ]
        return {**value, "model_profiles": profiles}

    @model_validator(mode="after")
    def validate_profiles(self):
        if not self.model_profiles:
            self.model_profiles = [ModelProfile(id="default", name="默认模型", config=self.model)]
            self.active_profile_id = "default"
        if len({profile.id for profile in self.model_profiles}) != len(self.model_profiles):
            raise ValueError("模型配置 ID 不能重复")
        if len({server.id for server in self.mcp_servers}) != len(self.mcp_servers):
            raise ValueError("MCP 配置 ID 不能重复")
        if not self.active_profile_id:
            self.active_profile_id = self.model_profiles[0].id
        selected = next(
            (profile for profile in self.model_profiles if profile.id == self.active_profile_id),
            None,
        )
        if not selected:
            raise ValueError("当前模型配置不存在，请重新选择")
        self.model = selected.config
        return self


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

    def version(self):
        return sha256(self.path.read_bytes() if self.path.exists() else b"").hexdigest()

    def prepare(self, settings: AppSettings, clear_keys=(), version=None) -> AppSettings:
        with self._lock:
            if version is not None and version != self.version():
                raise ValueError("设置已在其他窗口更新，请重新加载后合并修改")
            existing = {profile.id: profile for profile in self.load().model_profiles}
            for profile in settings.model_profiles:
                previous = existing.get(profile.id)
                if profile.id in clear_keys:
                    profile.config.api_key = ""
                elif not profile.config.api_key and previous:
                    profile.config.api_key = previous.config.api_key
            self.preserve_mcp_secrets(settings)
            return settings

    def save(
        self, settings: AppSettings, clear_key: bool = False, *, clear_keys=(), version=None
    ) -> None:
        with self._lock:
            cleared = {*clear_keys, *([settings.active_profile_id] if clear_key else [])}
            self.prepare(settings, cleared, version)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(self.path)

    def public(self) -> dict:
        with self._lock:
            settings = self.load()
            result = settings.model_dump()
            probes = self.read_probes()
            for profile in result["model_profiles"]:
                stored = next(item for item in settings.model_profiles if item.id == profile["id"])
                probe = probes.get(profile["id"])
                if probe and probe["fingerprint"] == model_fingerprint(stored.config):
                    profile["capabilities"] = probe["result"]
            for model in [
                result["model"],
                *(profile["config"] for profile in result["model_profiles"]),
            ]:
                model["has_api_key"] = bool(model["api_key"])
                model["api_key"] = ""
            for server in result["mcp_servers"]:
                server["headers"] = {key: SECRET_MASK for key in server["headers"]}
                server["env"] = {key: SECRET_MASK for key in server["env"]}
            result["version"] = self.version()
            return result

    def read_probes(self):
        path = self.path.with_name("model-probes.json")
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(rows, dict):
            return {}
        # 检测缓存可重新生成，损坏的条目不应阻止用户打开设置修复连接。
        return {
            key: row
            for key, row in rows.items()
            if isinstance(row, dict)
            and isinstance(row.get("fingerprint"), str)
            and isinstance(row.get("result"), dict)
        }

    def record_probe(self, profile_id, model, result):
        with self._lock:
            path = self.path.with_name("model-probes.json")
            probes = self.read_probes()
            probes[profile_id] = {"fingerprint": model_fingerprint(model), "result": result}
            temporary = path.with_suffix(".tmp")
            temporary.write_text(dump_json(probes), encoding="utf-8")
            temporary.replace(path)

    def preserve_mcp_secrets(self, settings: AppSettings) -> None:
        existing = {server.id: server for server in self.load().mcp_servers}
        for server in settings.mcp_servers:
            self.restore_server_secrets(server, existing.get(server.id))

    @staticmethod
    def restore_server_secrets(server, previous):
        for field in ("headers", "env"):
            values = getattr(server, field)
            stored = getattr(previous, field) if previous else {}
            for key, value in values.items():
                if value == SECRET_MASK:
                    if key not in stored:
                        raise ValueError("新的 MCP 凭据不能使用掩码，请填写实际值")
                    values[key] = stored[key]

    def prepare_server(self, server):
        with self._lock:
            previous = next(
                (item for item in self.load().mcp_servers if item.id == server.id), None
            )
            self.restore_server_secrets(server, previous)
            return server


def dump_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def model_fingerprint(model):
    return sha256(model.model_dump_json().encode()).hexdigest()
