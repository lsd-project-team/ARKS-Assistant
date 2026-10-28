"""用户仅能选择已有配置，不能借个人偏好接口修改系统参数。"""

from pydantic import BaseModel, ConfigDict, Field


class ModelPreferenceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(min_length=1, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
