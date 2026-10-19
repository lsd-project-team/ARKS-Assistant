"""场景和公开配置版本固定；凭据只允许由明确命名的环境变量提供。"""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import AppSettings, ModelSettings
from app.modules.code_changes.schemas import ProfileWrite
from app.modules.handover.domain.schemas import DebugIssue


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Case(Strict):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,60}$")
    kind: Literal["source_qa", "change", "debug_recall"]
    question: str = Field(min_length=1, max_length=20000)
    expected_sources: dict[str, str] = Field(min_length=1, max_length=100)
    rubric: dict[str, str] = Field(min_length=1, max_length=20)
    debug_issues: list[dict] = Field(default_factory=list, max_length=10)

    @field_validator("question")
    @classmethod
    def nonblank_question(cls, value):
        if not value.strip():
            raise ValueError("场景问题不能为空")
        return value

    @field_validator("rubric")
    @classmethod
    def nonblank_rubric(cls, value):
        if any(
            not key.strip() or not text.strip() or len(text) > 5000 for key, text in value.items()
        ):
            raise ValueError("rubric必须包含预先明确的非空标准")
        return value

    @model_validator(mode="after")
    def validated_fixtures(self):
        if self.kind == "debug_recall" and not self.debug_issues:
            raise ValueError("经验召回场景必须提供独立夹具")
        for item in self.debug_issues:
            if set(item) != {"title", "payload"} or not str(item["title"]).strip():
                raise ValueError("调试夹具必须明确title和payload")
            DebugIssue.model_validate(item["payload"])
        return self

    @field_validator("expected_sources")
    @classmethod
    def source_versions(cls, values):
        import re

        if any(not re.fullmatch(r"[a-f0-9]{64}", value) for value in values.values()):
            raise ValueError("场景必须填写真实 SHA256，不能使用占位版本")
        return values


class Suite(Strict):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,60}$")
    cases: list[Case] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def distinct_cases(self):
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("场景ID不能重复")
        return self


class ProviderConfig(Strict):
    model: dict
    key_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,79}$")
    # 只有显式null取消本套件额度拦截；实际用量与调用次数继续写入临时账本。
    token_limit: int | None = Field(default=100000, ge=1000, le=1000000)
    timeout_seconds: int = Field(default=180, ge=1, le=600)
    verification_profile: ProfileWrite | None = None

    @model_validator(mode="after")
    def public_config_only(self):
        if set(self.model) - (set(ModelSettings.model_fields) - {"api_key"}):
            raise ValueError("配置只允许公开模型字段；API密钥不得写入JSON")
        model = ModelSettings(**self.model)
        address = urlsplit(model.base_url)
        if not model.model or not model.base_url or address.query or address.fragment:
            raise ValueError("必须明确模型与供应商地址，地址不能包含query或fragment凭据")
        if self.verification_profile and self.verification_profile.executor.kind != "container":
            raise ValueError("质量套件的可选命令只允许显式配置固定镜像的沙箱")
        return self

    def settings(self, key):
        return AppSettings(
            model=ModelSettings(**self.model, api_key=key),
            auto_memory=False,
            mcp_servers=[],
            analysis={
                "mode": "standard",
                "standard_calls": 8,
                "deep_calls": 16,
                "verification_reserve": 2,
            },
        )

    def public(self):
        return {
            **self.model_dump(exclude={"key_env"}),
            "model": ModelSettings(**self.model).model_dump(exclude={"api_key"}),
        }
