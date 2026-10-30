"""应用用例输入；HTTP 与 Agent 共用相同字段约束。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.handover.domain.debug_issues import DebugContent
from app.modules.handover.domain.schemas import Kind


class Write(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Kind
    title: str = Field(min_length=1, max_length=200)
    payload: dict = Field(default_factory=dict)
    actor: str = Field(min_length=1, max_length=120)
    version: int | None = Field(default=None, ge=1)
    reason: str = Field(default="", max_length=2000)

    @field_validator("title", "actor")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("不能为空白")
        return value.strip()


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    actor: str = Field(min_length=1, max_length=120)
    role: str = Field(default="", max_length=120)
    opinion: str = Field(min_length=1, max_length=2000)

    @field_validator("actor", "opinion")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("请填写确认人和意见")
        return value.strip()


class DebugWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    payload: DebugContent
    version: int | None = Field(default=None, ge=1)

    @field_validator("title")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("请填写问题标题")
        return value.strip()
