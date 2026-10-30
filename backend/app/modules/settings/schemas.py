"""个人模型选择与全局指令的输入约束，不接受系统参数或目标账号。"""

from pydantic import BaseModel, ConfigDict, Field


class ModelPreferenceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(min_length=1, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")


class AgentInstructionsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(max_length=32768)
    version: str = Field(pattern=r"^[a-f0-9]{64}$")
