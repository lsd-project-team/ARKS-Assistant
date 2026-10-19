"""交接记录、不可变修订、原始附件和审计事件。"""

from sqlalchemy import ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.identifiers import new_id, now_iso
from app.infrastructure.database.base import Base


class HandoverRecord(Base):
    __tablename__ = "handover_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    # 只保留旧资料的来源项目身份；交接记录不再归属于对话项目。
    source_project_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
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


class HandoverDebugImage(Base):
    # 图片字节随 SQLite 一起备份；版本快照只保存有序引用，重复出现的位置不去重。
    __tablename__ = "handover_debug_images"
    record_id: Mapped[str] = mapped_column(ForeignKey("handover_records.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    media_type: Mapped[str] = mapped_column(String(100))
    content: Mapped[bytes] = mapped_column(LargeBinary)


class HandoverEvent(Base):
    __tablename__ = "handover_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_project_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    record_id: Mapped[str] = mapped_column(ForeignKey("handover_records.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(120))
    detail: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
