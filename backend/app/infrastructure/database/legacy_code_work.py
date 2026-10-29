"""已移除修改流程的历史表及共用模型额度表，仅供迁移和备份兼容。"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.identifiers import new_id, now_iso
from app.infrastructure.database.base import Base


class LegacyCodeChange(Base):
    __tablename__ = "code_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(160))
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="ready")
    source_root: Mapped[str] = mapped_column(Text)
    manifest_json: Mapped[str] = mapped_column(Text, default="{}")
    change_version: Mapped[str] = mapped_column(String(64), default="")
    files_changed: Mapped[int] = mapped_column(Integer, default=0)
    latest_verification_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    requirements_json: Mapped[str] = mapped_column(Text, default="{}")
    review_json: Mapped[str] = mapped_column(Text, default="{}")
    delivered_at: Mapped[str] = mapped_column(String(40), default="")


class LegacyVerificationProfile(Base):
    __tablename__ = "code_verification_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    argv_json: Mapped[str] = mapped_column(Text)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120)
    executor_json: Mapped[str] = mapped_column(Text, default='{"kind":"trusted_host"}')
    baseline_required: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str] = mapped_column(String(20), default="build")
    environment_label: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class LegacyVerification(Base):
    __tablename__ = "code_verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    change_id: Mapped[str] = mapped_column(ForeignKey("code_changes.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    profile_id: Mapped[str] = mapped_column(String(64))
    argv_json: Mapped[str] = mapped_column(Text)
    timeout_seconds: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[str] = mapped_column(String(20), default="change")
    executor_json: Mapped[str] = mapped_column(Text, default='{"kind":"trusted_host"}')
    source_version: Mapped[str] = mapped_column(String(64), default="")
    profile_version: Mapped[str] = mapped_column(String(64), default="")
    error_category: Mapped[str] = mapped_column(String(30), default="")
    change_version: Mapped[str] = mapped_column(String(64))
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    ended_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class ModelBudgetPolicy(Base):
    __tablename__ = "code_work_policies"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class ModelBudgetUsage(Base):
    __tablename__ = "code_work_usage"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    day: Mapped[str] = mapped_column(String(10), primary_key=True)
    reserved_tokens: Mapped[int] = mapped_column(Integer, default=0)
    actual_tokens: Mapped[int] = mapped_column(Integer, default=0)
    calls: Mapped[int] = mapped_column(Integer, default=0)


class ModelBudgetReservation(Base):
    __tablename__ = "code_work_reservations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[str] = mapped_column(String(10))
    reserved_tokens: Mapped[int] = mapped_column(Integer)
    actual_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
