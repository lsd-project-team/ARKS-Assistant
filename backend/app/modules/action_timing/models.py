"""原始采集包和可查询事件；同一作用域内运行批次不可变。"""

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.identifiers import new_id, now_iso
from app.infrastructure.database.base import Base


class TimingRun(Base):
    __tablename__ = "action_timing_runs"
    __table_args__ = (
        UniqueConstraint("scope_id", "source_run_id", name="uq_action_timing_scope_run"),
        Index("ix_action_timing_scope_created", "scope_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scope_id: Mapped[str] = mapped_column(String(160))
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_run_id: Mapped[str] = mapped_column(String(128))
    content_hash: Mapped[str] = mapped_column(String(64))
    file_hash: Mapped[str] = mapped_column(String(64))
    manifest_json: Mapped[str] = mapped_column(Text)
    package_json: Mapped[str] = mapped_column(Text, deferred=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class TimingSample(Base):
    __tablename__ = "action_timing_samples"
    __table_args__ = (
        UniqueConstraint("run_id", "event_id", name="uq_action_timing_run_event"),
        Index("ix_action_timing_samples_run_action", "run_id", "action_code", "start_ms"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("action_timing_runs.id"))
    event_id: Mapped[str] = mapped_column(String(128))
    action_code: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    start_ms: Mapped[float] = mapped_column(Float)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    event_json: Mapped[str] = mapped_column(Text)
