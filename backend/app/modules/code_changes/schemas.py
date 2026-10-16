"""HTTP 输入保持严格，模型只能选择已经保存的验证配置。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChangeWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    goal: str = Field(min_length=1, max_length=20000)

    @field_validator("title", "goal")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("标题和目标不能为空")
        return value.strip()


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


class VerificationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(min_length=1, max_length=64)
