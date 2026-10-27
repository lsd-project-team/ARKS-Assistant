"""原始采集包和可查询事件；同一作用域内运行批次不可变。"""

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.identifiers import new_id, now_iso
from app.infrastructure.database.base import Base


class TimingProject(Base):
    """设备/业务耗时项目独立保存，不引用聊天项目及其生命周期。"""

    __tablename__ = "action_timing_projects"
    id: Mapped[str] = mapped_column(String(160), primary_key=True, default=new_id)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


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


class TimingCategory(Base):
    __tablename__ = "action_timing_categories"
    __table_args__ = (UniqueConstraint("scope_id", "name_key", name="uq_timing_category_name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scope_id: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(60))
    name_key: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1)


class TimingAction(Base):
    __tablename__ = "action_timing_actions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scope_id: Mapped[str] = mapped_column(String(160), index=True)
    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("action_timing_categories.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120))
    name_key: Mapped[str] = mapped_column(String(240))
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


# SQLite 的普通唯一约束允许多个 NULL；未分类动作也必须按名称去重。
Index(
    "uq_timing_action_scope_category_name",
    TimingAction.scope_id,
    func.coalesce(TimingAction.category_id, ""),
    TimingAction.name_key,
    unique=True,
)
