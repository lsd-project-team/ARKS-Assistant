"""交接 HTTP 请求结构。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.handover.application.commands import Action
from app.modules.handover.domain.materials import MAX_TEXT


class Capture(BaseModel):
    source_project_id: str = Field(default="", max_length=32)
    supersedes: str = Field(default="", max_length=36)
    actor: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=2000)
    provider: str = Field(default="", max_length=2000)
    source_version: str = Field(default="", max_length=2000)
    device: str = Field(default="", max_length=2000)


class AIStart(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    action: str
    record_ids: list[str] = Field(min_length=1, max_length=20)


class TextSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=MAX_TEXT)
    actor: str = Field(min_length=1, max_length=120)
    provider: str = Field(default="", max_length=2000)
    source_version: str = Field(default="", max_length=2000)
    device: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=2000)
    supersedes: str = Field(default="", max_length=36)

    @field_validator("title", "actor")
    @classmethod
    def nonblank_name(cls, value):
        if not value.strip():
            raise ValueError("标题和整理人不能为空")
        return value.strip()

    @field_validator("content")
    @classmethod
    def nonblank_content(cls, value):
        if not value.strip():
            raise ValueError("文本内容不能为空")
        return value


class MaterialCapture(Action):
    source_project_id: str = Field(min_length=1, max_length=32)
    supersedes: str = Field(default="", max_length=36)


class Promotion(Action):
    title: str = Field(min_length=1, max_length=200)
    proposed: dict


class PackageCreate(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    record_ids: list[str] = Field(min_length=1, max_length=1000)
    recipient: str = Field(default="", max_length=2000)
    scope: str = Field(default="", max_length=100000)
    gaps: str = Field(default="", max_length=100000)
