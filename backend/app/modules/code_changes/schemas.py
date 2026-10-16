"""HTTP 输入保持严格，模型只能选择已经保存的验证配置。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ExecutorWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["container", "trusted_host"] = "container"
    platform: Literal["linux", "windows"] = "linux"
    image: str = Field(default="", max_length=500)
    context: str = Field(default="default", pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")

    @model_validator(mode="after")
    def immutable_container_image(self):
        if self.kind == "container":
            import re

            if not re.fullmatch(r"(?:[A-Za-z0-9._:/-]+@)?sha256:[a-f0-9]{64}", self.image):
                raise ValueError("容器镜像必须填写已准备的固定sha256身份，不能使用浮动标签")
        return self


class CodeWorkPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_storage_mb: int = Field(default=4096, ge=100, le=1_000_000)
    min_free_mb: int = Field(default=1024, ge=0, le=1_000_000)
    max_log_mb: int = Field(default=16, ge=1, le=1024)
    max_active_verifications: int = Field(default=1, ge=1, le=16)
    retention_days: int = Field(default=30, ge=1, le=3650)
    reading_token_limit: int = Field(default=500000, ge=1000, le=100_000_000)
    require_sandbox_delivery: bool = True


class ChangeWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    goal: str = Field(min_length=1, max_length=20000)
    acceptance_criteria: list[str] = Field(default_factory=list, max_length=50)
    constraints: str = Field(default="", max_length=10000)
    allowed_paths: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("title", "goal")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("标题和目标不能为空")
        return value.strip()

    @field_validator("acceptance_criteria", "allowed_paths")
    @classmethod
    def bounded_lines(cls, values):
        result = [value.strip() for value in values if value.strip()]
        if any(len(value) > 2000 or "\x00" in value for value in result):
            raise ValueError("单条验收标准或范围最多2000字且不能含NUL")
        return list(dict.fromkeys(result))

    @field_validator("allowed_paths")
    @classmethod
    def relative_scope(cls, values):
        for value in values:
            path = value.replace("\\", "/")
            if path.startswith("/") or ":" in path or ".." in path.split("/"):
                raise ValueError("修改范围必须是源码内的相对路径或glob，不能越界")
        return [value.replace("\\", "/") for value in values]


class FileEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=1000)
    before: str = Field(max_length=2_000_000)
    after: str = Field(max_length=2_000_000)
    version: str = Field(max_length=64)


class ProfileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=120)
    argv: list[str] = Field(min_length=1, max_length=100)
    timeout_seconds: int = Field(default=120, ge=1, le=600)
    executor: ExecutorWrite
    baseline_required: bool = True
    category: Literal["build", "test", "analysis", "offline"] = "build"
    environment_label: str = Field(default="", max_length=200)


class VerificationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(min_length=1, max_length=64)
    purpose: Literal["baseline", "change"] = "change"


class ReviewWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    change_version: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]+$")
    notes: str = Field(default="", max_length=5000)


class CleanupWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dry_run: bool = True
