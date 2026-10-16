"""统计只保存采集事实，不根据旧消息推算访问或使用时长。"""

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, new_id, now_iso


class CollectionState(Base):
    __tablename__ = "usage_collection"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    started_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class UsageVisit(Base):
    __tablename__ = "usage_visits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[str] = mapped_column(String(40), default=now_iso, index=True)
    last_seen: Mapped[str] = mapped_column(String(40), default=now_iso)


class UsageActivity(Base):
    __tablename__ = "usage_activity"
    __table_args__ = (Index("ix_usage_activity_account_time", "account_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    visit_id: Mapped[str] = mapped_column(ForeignKey("usage_visits.id"))
    active_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso, index=True)


class BusinessSubmission(Base):
    __tablename__ = "business_submissions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), index=True)
    category: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso, index=True)


class AdminEvent(Base):
    __tablename__ = "admin_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(160))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso, index=True)
