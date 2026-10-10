"""公共请求模型；选区快照与运行状态有独立含义，不使用散落的参数列表。"""

from pydantic import BaseModel, Field, model_validator


class ThreadCreate(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=120)


class ThreadUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


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


class SummaryCorrection(BaseModel):
    summary: str = Field(min_length=1, max_length=50000)
    version: str = Field(min_length=1, max_length=100)
