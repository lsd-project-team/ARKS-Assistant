"""调试现象和处理结果的业务约束。"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DebugContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    resolution_status: Literal["open", "resolved"] = "open"
    keywords: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list, max_length=20
    )
    notes: str = Field(default="", max_length=30000)

    @field_validator("problem")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("请填写问题现象")
        return value

    @model_validator(mode="after")
    def resolved_solution(self):
        if self.resolution_status == "resolved" and not self.solution.strip():
            raise ValueError("标记已解决时请填写解决办法")
        return self
