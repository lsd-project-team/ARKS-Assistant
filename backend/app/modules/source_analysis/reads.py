"""相邻源码范围合并读取；只把实际返回的正文登记为证据。"""

import json

from pydantic import BaseModel, Field, model_validator

from app.agents.context.tokens import text_tokens
from app.modules.source_analysis.evidence import source_excerpt
from app.modules.source_analysis.location import resolve_source_path


class SourceRange(BaseModel):
    path: str = Field(min_length=1, max_length=512)
    start_line: int = Field(default=1, ge=1)
    end_line: int = Field(default=200, ge=1)
    reason: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_line < self.start_line or self.end_line - self.start_line >= 500:
            raise ValueError("源码范围应按顺序且每段不超过 500 行")
        return self


def merged_ranges(ranges):
    normalized = [SourceRange.model_validate(row).model_dump() for row in ranges]
    normalized.sort(key=lambda row: (row["path"].removeprefix("/workspace/"), row["start_line"]))
    merged = []
    for row in normalized:
        row["path"] = row["path"].removeprefix("/workspace/")
        previous = merged[-1] if merged else None
        if (
            previous
            and previous["path"] == row["path"]
            and row["start_line"] <= previous["end_line"] + 8
            and max(previous["end_line"], row["end_line"]) - previous["start_line"] < 500
        ):
            previous["end_line"] = max(previous["end_line"], row["end_line"])
        else:
            merged.append(row)
    return merged


def batch_source(workspace, ranges, evidence=None):
    if not 1 <= len(ranges) <= 12:
        raise ValueError("批量读取每次应包含 1–12 段源码")
    rows = merged_ranges(ranges)
    result = {"reads": [], "errors": [], "remaining": []}
    line_count = 0
    for row in rows:
        try:
            excerpt = source_excerpt(
                workspace,
                resolve_source_path(workspace, row["path"]),
                row["start_line"],
                row["end_line"],
            )
            available_lines = max(0, 1200 - line_count)
            first, last = 0, min(available_lines, len(excerpt["lines"]))
            # 返回实际可容纳的前缀，剩余行单独列出，不能整段假装已读。
            while first < last:
                candidate_count = (first + last + 1) // 2
                candidate = {**excerpt, "lines": excerpt["lines"][:candidate_count]}
                if (
                    text_tokens(
                        json.dumps([*result["reads"], candidate], ensure_ascii=False, indent=2)
                    )
                    <= 11000
                ):
                    first = candidate_count
                else:
                    last = candidate_count - 1
            if first < len(excerpt["lines"]):
                result["remaining"].append({**row, "start_line": excerpt["lines"][first]["line"]})
                if not first:
                    continue
                excerpt = {**excerpt, "lines": excerpt["lines"][:first]}
            result["reads"].append(excerpt)
            line_count += len(excerpt["lines"])
            if evidence:
                evidence.record(excerpt, "read_source_batch")
        except (ValueError, OSError) as error:
            result["errors"].append({**row, "error": str(error)})
    return result
