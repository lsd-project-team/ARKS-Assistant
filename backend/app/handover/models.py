"""交接记录、不可变修订、原始附件和审计事件。"""

from sqlalchemy import ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, new_id, now_iso


class HandoverRecord(Base):
    __tablename__ = "handover_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    title: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(24), default="draft")
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class HandoverRevision(Base):
    __tablename__ = "handover_revisions"
    __table_args__ = (Index("ix_handover_revision", "record_id", "version", unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(ForeignKey("handover_records.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(24))
    payload_json: Mapped[str] = mapped_column(Text)
    confirmation_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class HandoverBlob(Base):
    # 附件跟随原有 SQLite 备份，不引入旧备份工具无法恢复的外部目录。
    __tablename__ = "handover_blobs"
    record_id: Mapped[str] = mapped_column(ForeignKey("handover_records.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(250))
    media_type: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary)


class HandoverEvent(Base):
    __tablename__ = "handover_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    record_id: Mapped[str] = mapped_column(ForeignKey("handover_records.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(120))
    detail: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
