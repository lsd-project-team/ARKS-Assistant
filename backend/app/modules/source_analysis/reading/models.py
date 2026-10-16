"""持久保存阅读快照、逐文件断点和各次分析成果。"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.identifiers import new_id, now_iso
from app.infrastructure.database.base import Base


class ProjectReadingJob(Base):
    __tablename__ = "project_reading_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="ready")
    snapshot_version: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    error: Mapped[str] = mapped_column(Text, default="")


class ProjectReadingFile(Base):
    __tablename__ = "project_reading_files"
    __table_args__ = (UniqueConstraint("job_id", "path"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("project_reading_jobs.id"), index=True)
    path: Mapped[str] = mapped_column(Text)
    module: Mapped[str] = mapped_column(Text)
    source_version: Mapped[str] = mapped_column(String(64), default="")
    encoding: Mapped[str] = mapped_column(String(20), default="utf-8-sig")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    next_chunk: Mapped[int] = mapped_column(Integer, default=0)
    read_chunks: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")


class ProjectReadingDocument(Base):
    __tablename__ = "project_reading_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("project_reading_jobs.id"), index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("project_reading_files.id"), index=True)
    path: Mapped[str] = mapped_column(Text)
    module: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_version: Mapped[str] = mapped_column(String(64))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="analyzed")
    latest: Mapped[bool] = mapped_column(Boolean, default=True)
    summary: Mapped[str] = mapped_column(Text)
    entrypoints_json: Mapped[str] = mapped_column(Text, default="[]")
    dependencies_json: Mapped[str] = mapped_column(Text, default="[]")
    unknowns_json: Mapped[str] = mapped_column(Text, default="[]")
    references_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
