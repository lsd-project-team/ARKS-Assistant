"""项目身份、源码关联与历史资料模型。"""

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.identifiers import new_id, now_iso
from app.infrastructure.database.base import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_owner_state", "owner_id", "state"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    source_root: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_folders_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    deepwiki_repo: Mapped[str] = mapped_column(String(200), default="", server_default="")
    state: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    pinned_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


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
