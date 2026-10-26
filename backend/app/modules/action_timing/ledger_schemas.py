"""台账表单与导入契约；耗时以秒保存，空值与零值分开。"""

import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator

MAX_ROWS = 5000
MAX_FILE_BYTES = 5 * 1024 * 1024
DurationStatus = Literal["all", "filled", "missing"]
DuplicateMode = Literal["skip", "update"]


def name_key(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


class LedgerInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def reject_control_characters(cls, value):
        if isinstance(value, str) and any(
            (ord(char) < 32 and char not in "\t\n\r")
            or 0xD800 <= ord(char) <= 0xDFFF
            or ord(char) in {0xFFFE, 0xFFFF}
            for char in value
        ):
            raise ValueError("文本包含无法保存到Excel的控制字符")
        return value


class CategoryInput(LedgerInput):
    name: str = Field(min_length=1, max_length=60)

    @field_validator("name")
    @classmethod
    def reserved_name(cls, value):
        if name_key(value) == name_key("未分类"):
            raise ValueError("未分类为系统保留分类，请使用其他名称")
        return value


class CategoryUpdate(CategoryInput):
    version: int = Field(ge=1)


class CategoryDelete(LedgerInput):
    version: int = Field(ge=1)
    target_id: str | None = Field(default=None, max_length=36)


class ActionInput(LedgerInput):
    name: str = Field(min_length=1, max_length=120)
    category_id: str | None = Field(default=None, max_length=36)
    duration_seconds: Annotated[FiniteFloat, Field(ge=0)] | None = None
    notes: str = Field(default="", max_length=1000)

    @field_validator("duration_seconds", mode="before")
    @classmethod
    def reject_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("耗时须为非负数或留空")
        return value


class ActionUpdate(ActionInput):
    version: int = Field(ge=1)


class ImportRow(LedgerInput):
    row_number: int = Field(ge=2, le=MAX_ROWS + 1)
    category: str = Field(default="", max_length=60)
    name: str = Field(min_length=1, max_length=120)
    duration_seconds: Annotated[FiniteFloat, Field(ge=0)] | None = None
    notes: str = Field(default="", max_length=1000)

    _duration = field_validator("duration_seconds", mode="before")(ActionInput.reject_boolean)


class ImportCommit(LedgerInput):
    rows: list[ImportRow] = Field(min_length=1, max_length=MAX_ROWS)
    mode: DuplicateMode = "skip"
    revision: str = Field(min_length=64, max_length=64)
