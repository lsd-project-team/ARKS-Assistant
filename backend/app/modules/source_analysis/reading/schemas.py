"""阅读模型的结构化结果与 HTTP 请求。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReadingReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=2048)
    source_version: str = Field(min_length=1, max_length=64)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_line < self.start_line:
            raise ValueError("引用结束行不能早于开始行")
        return self


class ReadingAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=12000)
    entrypoints: list[str] = Field(default_factory=list, max_length=50)
    dependencies: list[str] = Field(default_factory=list, max_length=100)
    dependency_paths: list[str] = Field(default_factory=list, max_length=100)
    unknowns: list[str] = Field(default_factory=list, max_length=100)
    references: list[ReadingReference] = Field(default_factory=list, max_length=100)

    @field_validator("summary")
    @classmethod
    def nonblank_summary(cls, value):
        if not value.strip():
            raise ValueError("分析摘要不能为空")
        return value.strip()


class ReadingCreate(BaseModel):
    title: str = Field(default="项目全量阅读", max_length=200)


class ReadingReview(BaseModel):
    version: int = Field(ge=1)
    decision: Literal["approved", "needs_changes"]


class ReadingStart(BaseModel):
    max_chunks: int = Field(default=64, ge=1, le=256)
