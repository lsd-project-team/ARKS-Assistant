"""项目阅读与隔离开发档案；不改写业务源码、现有记录或账号。"""

import sqlalchemy as sa
from alembic import op

from app.infrastructure.database.registry import Base

revision = "0019"
down_revision = "0018"
branch_labels = depends_on = None

TABLES = (
    "code_changes",
    "code_verification_profiles",
    "code_verifications",
)


def historical_reading_tables():
    # 只在迁移中保留历史表定义，应用不注册、不读取或创建阅读任务。
    metadata = sa.MetaData()
    jobs = sa.Table(
        "project_reading_jobs",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(100), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("snapshot_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("error", sa.Text, nullable=False),
    )
    files = sa.Table(
        "project_reading_files",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(100), nullable=False, index=True),
        sa.Column("job_id", sa.ForeignKey("project_reading_jobs.id"), nullable=False, index=True),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("module", sa.Text, nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("encoding", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        *[
            sa.Column(name, sa.Boolean, nullable=False)
            for name in ("indexed", "read", "analyzed", "reviewed", "stale")
        ],
        sa.Column("next_chunk", sa.Integer, nullable=False),
        sa.Column("read_chunks", sa.Integer, nullable=False),
        sa.Column("error", sa.Text, nullable=False),
        sa.UniqueConstraint("job_id", "path"),
    )
    documents = sa.Table(
        "project_reading_documents",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(100), nullable=False, index=True),
        sa.Column("job_id", sa.ForeignKey("project_reading_jobs.id"), nullable=False, index=True),
        sa.Column("file_id", sa.ForeignKey("project_reading_files.id"), nullable=False, index=True),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("module", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("start_line", sa.Integer, nullable=False),
        sa.Column("end_line", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("latest", sa.Boolean, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        *[
            sa.Column(name, sa.Text, nullable=False)
            for name in (
                "entrypoints_json",
                "dependencies_json",
                "unknowns_json",
                "references_json",
            )
        ],
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("reviewed_at", sa.String(40)),
    )
    return jobs, files, documents


def upgrade():
    for table in historical_reading_tables():
        table.create(op.get_bind(), checkfirst=True)
    for name in TABLES:
        Base.metadata.tables[name].create(op.get_bind(), checkfirst=True)


def downgrade():
    for name in reversed(TABLES):
        op.drop_table(name)
    for table in reversed(historical_reading_tables()):
        op.drop_table(table.name)
