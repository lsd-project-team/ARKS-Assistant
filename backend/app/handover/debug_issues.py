"""调试经验共用交接存储；录入身份和对话原文由服务端维护。"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select

from app.handover.models import HandoverRecord
from app.handover.schemas import DebugIssue, Write
from app.handover.store import HandoverStore, record_dict


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


class DebugWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    payload: DebugContent
    version: int | None = Field(default=None, ge=1)

    @field_validator("title")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("请填写问题标题")
        return value.strip()


def actor_name(actor):
    return actor.get("display_name") or actor.get("username") or "对话录入"


class DebugIssues:
    def __init__(self, database, projects=None):
        self.database = database
        self.store = HandoverStore(projects, database=database)

    def rows(self, include_archived=False):
        with self.database.session() as session:
            statement = select(HandoverRecord).where(HandoverRecord.kind == "debug_issue")
            if not include_archived:
                statement = statement.where(HandoverRecord.state != "archived")
            return [
                record_dict(row)
                for row in session.scalars(
                    statement.order_by(HandoverRecord.updated_at.desc(), HandoverRecord.id)
                )
            ]

    def save(self, body, actor, identifier=None):
        payload = body.payload.model_dump()
        if identifier:
            previous = self.store.get(identifier)
            if previous["kind"] != "debug_issue":
                raise ValueError("不是调试问题记录")
            if previous["state"] == "archived":
                raise ValueError("请先恢复归档记录")
            payload = {**previous["payload"], **payload}
            return self.store.update(
                identifier,
                Write(
                    kind="debug_issue",
                    title=body.title,
                    payload=payload,
                    actor=actor_name(actor),
                    version=body.version,
                    reason="更新调试问题与处理结果",
                ),
            )
        payload.update(origin="human", reported_by=actor_name(actor))
        return self.store.create("debug_issue", body.title, payload, actor_name(actor))

    def captured(self, message_id):
        return next(
            (
                row
                for row in self.rows(True)
                if row["payload"].get("source_message_id") == message_id
            ),
            None,
        )

    def capture(self, title, payload, original, message, project_id):
        # 同一条消息的恢复、重试和重新生成只对应一条记录。
        with self.store.lock:
            existing = self.captured(message["id"])
            if existing:
                return existing
            actor = message.get("actor") or {}
            value = DebugIssue.model_validate(
                {
                    **payload,
                    "origin": "ai",
                    "original_text": original,
                    "reported_by": actor_name(actor),
                    "source_message_id": message["id"],
                    "source_thread_id": message["thread_id"],
                    "source_project_id": project_id or "",
                }
            ).model_dump()
            return self.store.create("debug_issue", title, value, actor_name(actor))
