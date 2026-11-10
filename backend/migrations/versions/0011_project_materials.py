"""Versioned project documents, confirmed conclusions and additional source roots."""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = depends_on = None


def historical_tables():
    # 历史迁移自行定义旧结构，不再依赖已退出应用的 ORM；已有库和备份仍能升级。
    metadata = sa.MetaData()
    sa.Table("projects", metadata, sa.Column("id", sa.String(32), primary_key=True))
    materials = sa.Table(
        "project_materials",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("source_name", sa.String(250), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("origin_thread_id", sa.String(36)),
        sa.Column("origin_message_id", sa.String(36)),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )
    revisions = sa.Table(
        "project_material_revisions",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_id", sa.ForeignKey("project_materials.id"), nullable=False, index=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Index("ix_material_version", "material_id", "version", unique=True),
    )
    return materials, revisions


def upgrade():
    bind = op.get_bind()
    if "source_folders_json" not in {
        row["name"] for row in sa.inspect(bind).get_columns("projects")
    }:
        op.add_column(
            "projects",
            sa.Column("source_folders_json", sa.Text, nullable=False, server_default="[]"),
        )
    for table in historical_tables():
        table.create(bind, checkfirst=True)


def downgrade():
    op.drop_table("project_material_revisions")
    op.drop_table("project_materials")
    op.drop_column("projects", "source_folders_json")
