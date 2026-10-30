"""交接记录的版本与审核状态规则，不依赖数据库或 HTTP。"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.modules.handover.domain.rules import confirmation_gate, linked_ids


def assert_version(actual, expected):
    if actual != expected:
        raise ValueError("记录已被更新。草稿已保留，请读取新版本后合并修改")


@dataclass(frozen=True, slots=True)
class ReviewOutcome:
    state: str
    linked_versions: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class Record:
    id: str
    kind: str
    version: int
    state: str
    payload: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, row):
        return cls(row["id"], row["kind"], row["version"], row["state"], row["payload"])

    def review(self, action, records) -> ReviewOutcome:
        if self.kind == "job":
            raise ValueError("请使用运行的取消或重试操作")
        if action == "confirm":
            return self._confirm(records)
        if action == "reject":
            if self.kind == "package":
                raise ValueError("交接包仅使用未确认和已确认状态")
            if self.kind in {"task", "candidate"}:
                raise ValueError("工作项和 AI 候选请使用各自的处理入口")
            if self.state not in {"draft", "needs_review"}:
                raise ValueError("仅待确认或待重新复核的内容可以拒绝")
            return ReviewOutcome("rejected", {})
        if action == "archive":
            return ReviewOutcome("archived", {})
        if action == "restore":
            return ReviewOutcome("needs_review", {})
        raise ValueError("无效的确认操作")

    def _confirm(self, records):
        errors = {
            "confirmed": "此版本已经确认；内容变化时请先编辑并保存新版本",
            "archived": "请先恢复记录",
            "rejected": "此内容已被拒绝，请补充并保存新版本后重新审核",
        }
        if self.kind == "package":
            errors.pop("rejected")
        if self.state in errors:
            raise ValueError(errors[self.state])
        # supersedes 是历史链路，旧资料被拒绝不阻止补充后的新资料审核。
        current_links = linked_ids({**self.payload, "supersedes": ""})
        if any(records[key]["state"] == "rejected" for key in current_links):
            raise ValueError("关联内容已被拒绝，请复核来源后再确认")
        confirmation_gate(
            {"id": self.id, "kind": self.kind, "state": self.state, "payload": self.payload},
            records,
        )
        for reference in self.payload.get("evidence", []):
            if records[reference["record_id"]]["version"] != reference["version"]:
                raise ValueError("来源有新版本，请复核并更新引用后确认")
        return ReviewOutcome(
            "confirmed", {key: records[key]["version"] for key in linked_ids(self.payload)}
        )
