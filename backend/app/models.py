"""业务存储与 Agent 检查点独立，压缩不会删除原始消息。"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class Thread(Base):
    __tablename__ = "threads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    state: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    deleted_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pinned_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_read_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    auto_title: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    origin_thread_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    origin_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    thread_id: Mapped[str] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    selections_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    thread_id: Mapped[str] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    answer: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    resumed_from: Mapped[str | None] = mapped_column(String(36), nullable=True)
    regenerated_from: Mapped[str | None] = mapped_column(String(36), nullable=True)
    response_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (Index("ix_run_event_cursor", "run_id", "sequence", unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class MemoryRecord(Base):
    __tablename__ = "memory_records"
    id: Mapped[str] = mapped_column(String(250), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    scope: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))
    source_thread_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_paths_json: Mapped[str] = mapped_column(Text, default="[]")
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)
