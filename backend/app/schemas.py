"""公共请求模型；选区快照与运行状态有独立含义，不使用散落的参数列表。"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ThreadCreate(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=120)


class ThreadUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    state: Literal["active", "archived"] | None = None
    pinned: bool | None = None

    @model_validator(mode="after")
    def validate_change(self):
        if self.title is None and self.state is None and self.pinned is None:
            raise ValueError("请指定要修改的会话信息")
        if self.title is not None:
            self.title = self.title.strip()
            if not self.title:
                raise ValueError("对话标题不能为空")
        return self


class PinnedOrder(BaseModel):
    ids: list[str] = Field(max_length=200)


class PinMove(BaseModel):
    direction: Literal[-1, 1]


class CodeSelection(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    start_column: int = Field(default=1, ge=1)
    end_column: int = Field(default=1, ge=1)
    content: str = Field(min_length=1, max_length=60000)
    version: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_line < self.start_line:
            raise ValueError("结束行不能小于开始行")
        if self.end_line == self.start_line and self.end_column < self.start_column:
            raise ValueError("结束列不能小于开始列")
        return self


class RunCreate(BaseModel):
    content: str = Field(min_length=1, max_length=30000)
    selections: list[CodeSelection] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_content(self):
        self.content = self.content.strip()
        if not self.content:
            raise ValueError("消息不能为空")
        return self


class QueueEdit(RunCreate):
    version: str = Field(min_length=1, max_length=40)


class BranchCreate(BaseModel):
    message_id: str = Field(min_length=1, max_length=36)


class MemoryWrite(BaseModel):
    name: str = Field(pattern=r"^[\w\-\u4e00-\u9fff]{1,80}\.md$")
    content: str = Field(max_length=50000)
    scope: str = Field(default="project", pattern=r"^(project|user)$")
    version: str | None = None
    source_thread_id: str | None = None
    source_paths: list[str] = Field(default_factory=list)


class SettingsWrite(BaseModel):
    settings: dict
    clear_api_key: bool = False
    clear_profile_keys: list[str] = Field(default_factory=list, max_length=20)
    version: str | None = None


class ModelProbe(BaseModel):
    settings: dict | None = None
    profile_id: str | None = None
    clear_profile_keys: list[str] = Field(default_factory=list, max_length=20)
    version: str | None = None


class McpProbe(BaseModel):
    server: dict | None = None


class SummaryCorrection(BaseModel):
    summary: str = Field(min_length=1, max_length=50000)
    version: str = Field(min_length=1, max_length=100)
