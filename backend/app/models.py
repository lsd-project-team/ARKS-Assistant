"""业务存储与 Agent 检查点独立，压缩不会删除原始消息。"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    source_root: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_folders_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    instructions: Mapped[str] = mapped_column(Text, default="", server_default="")
    deepwiki_repo: Mapped[str] = mapped_column(String(200), default="", server_default="")
    state: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    pinned_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class SourceWorkspace(Base):
    """引用保存源码根目录身份，移动对话不会把旧链接指向另一个项目。"""

    __tablename__ = "source_workspaces"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    root: Mapped[str] = mapped_column(Text)


class SourcePreference(Base):
    """按项目保存默认来源；独立对话使用独立 scope_id，不共享项目配置。"""

    __tablename__ = "source_preferences"
    scope_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    options_json: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)


class ProjectMaterial(Base):
    __tablename__ = "project_materials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="document")
    source_name: Mapped[str] = mapped_column(String(250), default="")
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(20), default="active")
    origin_thread_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    origin_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class ProjectMaterialRevision(Base):
    """不可变的资料快照，让旧回答的引用不随资料编辑而变化。"""

    __tablename__ = "project_material_revisions"
    __table_args__ = (Index("ix_material_version", "material_id", "version", unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("project_materials.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class Thread(Base):
    __tablename__ = "threads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
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
