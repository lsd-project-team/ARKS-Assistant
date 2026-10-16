"""数据库表结构保持不变，按业务模块组织模型。"""

from sqlalchemy import Integer, String, Text
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
