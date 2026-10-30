"""项目阅读与隔离开发档案；不改写业务源码、现有记录或账号。"""

from alembic import op

from app.infrastructure.database.registry import Base

revision = "0019"
down_revision = "0018"
branch_labels = depends_on = None

TABLES = (
    "project_reading_jobs",
    "project_reading_files",
    "project_reading_documents",
    "code_changes",
    "code_verification_profiles",
    "code_verifications",
)


def upgrade():
    for name in TABLES:
        Base.metadata.tables[name].create(op.get_bind(), checkfirst=True)


def downgrade():
    for name in reversed(TABLES):
        op.drop_table(name)
