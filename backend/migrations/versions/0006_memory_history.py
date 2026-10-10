"""记忆覆盖及删除操作保留历史快照，不删除既有 Markdown 文件。"""

from alembic import op

from app.models import MemoryRevision

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    MemoryRevision.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table("memory_revisions")
