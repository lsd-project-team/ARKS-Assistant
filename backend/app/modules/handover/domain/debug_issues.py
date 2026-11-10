"""调试现象和处理结果的业务约束。"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator


class LegacyDebugContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_type: Literal["problem", "experience", "progress", "archive"] = "problem"
    occurred_on: str = Field(default="", max_length=2000)
    recorded_by: str = Field(default="", max_length=2000)
    recorded_at: str = Field(default="", max_length=2000)
    problem: str = Field(min_length=1, max_length=30000)
    conditions: str = Field(default="", max_length=30000)
    environment: str = Field(default="", max_length=30000)
    device: str = Field(default="", max_length=2000)
    software_version: str = Field(default="", max_length=2000)
    module: str = Field(default="", max_length=2000)
    investigation: str = Field(default="", max_length=30000)
    cause: str = Field(default="", max_length=30000)
    solution: str = Field(default="", max_length=30000)
    verification: str = Field(default="", max_length=30000)
    resolution_status: Literal["open", "resolved", "recorded"] = "open"
    keywords: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list, max_length=20
    )
    notes: str = Field(default="", max_length=30000)

    @field_validator("problem")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("请填写记录内容")
        return value

    @model_validator(mode="after")
    def resolved_solution(self):
        # 普通工作进展和经验没有“解决/未解决”的含义，不生成虚假的待办状态。
        if self.record_type != "problem":
            self.resolution_status = "recorded"
        elif self.resolution_status == "recorded":
            raise ValueError("问题处理请选择未解决或已解决")
        if self.resolution_status == "resolved" and not self.solution.strip():
            raise ValueError("标记已解决时请填写解决办法")
        return self


class DebugAttributes(BaseModel):
    """可编辑的metadata；录入账号、原文、来源与原图只能由服务端维护。"""

    model_config = ConfigDict(extra="forbid")
    record_type: Literal["problem", "experience", "progress", "archive"] = "problem"
    resolution_status: Literal["open", "resolved", "recorded"] = "open"
    occurred_on: str = Field(default="", max_length=2000)
    recorded_by: str = Field(default="", max_length=2000)
    recorded_at: str = Field(default="", max_length=2000)
    device: str = Field(default="", max_length=2000)
    software_version: str = Field(default="", max_length=2000)
    module: str = Field(default="", max_length=2000)
    conditions: str = Field(default="", max_length=30000)
    environment: str = Field(default="", max_length=30000)
    investigation: str = Field(default="", max_length=30000)
    cause: str = Field(default="", max_length=30000)
    verification: str = Field(default="", max_length=30000)
    notes: str = Field(default="", max_length=30000)

    @model_validator(mode="after")
    def status(self):
        if self.record_type != "problem":
            self.resolution_status = "recorded"
        elif self.resolution_status == "recorded":
            raise ValueError("问题处理请选择未解决或已解决")
        return self


class DebugContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=30000)
    answer: str = Field(min_length=1, max_length=100000)
    keywords: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list, max_length=20
    )
    metadata: DebugAttributes = Field(default_factory=DebugAttributes)
    _input_text: str = PrivateAttr(default="")

    @model_validator(mode="wrap")
    @classmethod
    def preserve_input(cls, value, handler):
        result = handler(value)
        if isinstance(value, dict):
            result._input_text = value.get("problem", "") or (
                str(value.get("question", "")) + "\n\n" + str(value.get("answer", ""))
            )
        return result

    @model_validator(mode="before")
    @classmethod
    def legacy(cls, value):
        if isinstance(value, dict) and "question" not in value and "answer" not in value:
            from app.modules.handover.domain.debug_knowledge import knowledge_payload

            result = knowledge_payload(LegacyDebugContent.model_validate(value).model_dump())
            result["metadata"] = {
                key: item
                for key, item in result["metadata"].items()
                if key in DebugAttributes.model_fields
            }
            return result
        return value

    @field_validator("question", "answer")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("请填写问题和答案")
        return value.strip()
