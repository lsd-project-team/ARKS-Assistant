"""数据库表结构保持不变，按业务模块组织模型。"""

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.identifiers import now_iso
from app.infrastructure.database.base import Base


class MemoryRecord(Base):
    __tablename__ = "memory_records"
    id: Mapped[str] = mapped_column(String(250), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    scope: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))
    source_thread_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_paths_json: Mapped[str] = mapped_column(Text, default="[]")
    lifecycle: Mapped[str] = mapped_column(String(20), default="valid")
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class MemoryRevision(Base):
    __tablename__ = "memory_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    memory_id: Mapped[str] = mapped_column(String(250), index=True)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(100))
    scope: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(64))
    source_thread_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_paths_json: Mapped[str] = mapped_column(Text, default="[]")
    lifecycle: Mapped[str] = mapped_column(String(20), default="valid")
    action: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class MemoryExtraction(Base):
    """每个聊天固定输入指纹；租约到期后可恢复，提取成果可单独重试整理。"""

    __tablename__ = "memory_extractions"
    __table_args__ = (Index("ix_memory_extraction_owner_workspace", "owner_id", "workspace_id"),)
    thread_id: Mapped[str] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True
    )
    owner_id: Mapped[str] = mapped_column(String(36))
    workspace_id: Mapped[str] = mapped_column(String(64))
    fingerprint: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(24), default="pending")
    raw_json: Mapped[str] = mapped_column(Text, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str] = mapped_column(String(36), default="")
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    retry_after: Mapped[float] = mapped_column(Float, default=0)
    error_code: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class MemoryBundle(Base):
    """数据库保存已发布的完整快照；Markdown 为同版本的可读投影。"""

    __tablename__ = "memory_bundles"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True)
    document_json: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)
