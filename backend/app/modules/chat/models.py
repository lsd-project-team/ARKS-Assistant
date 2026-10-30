"""数据库表结构保持不变，按业务模块组织模型。"""

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.identifiers import new_id, now_iso
from app.infrastructure.database.base import Base


class Thread(Base):
    __tablename__ = "threads"
    __table_args__ = (
        Index("ix_threads_owner_workspace_state", "owner_id", "workspace_id", "state"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    context_generation: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
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
    queue_paused: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    thread_id: Mapped[str] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    selections_json: Mapped[str] = mapped_column(Text, default="[]")
    source_options_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    context_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    replaces_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    origin_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_workspace_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")


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
    reset_context: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    stage: Mapped[str] = mapped_column(String(40), default="queued", server_default="queued")
    error_code: Mapped[str] = mapped_column(String(40), default="", server_default="")
    model_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    project_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    started_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
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


class QueuedQuestion(Base):
    __tablename__ = "queued_questions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    thread_id: Mapped[str] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    selections_json: Mapped[str] = mapped_column(Text, default="[]")
    source_options_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
