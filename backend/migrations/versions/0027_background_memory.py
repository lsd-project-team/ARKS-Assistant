"""新增后台记忆提取与发布状态，旧记忆及原始对话留存。"""

from alembic import op

from app.modules.memory.models import MemoryBundle, MemoryExtraction

revision = "0027"
down_revision = "0026"
branch_labels = depends_on = None


def upgrade():
    for table in (MemoryExtraction.__table__, MemoryBundle.__table__):
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    for table in (MemoryBundle.__table__, MemoryExtraction.__table__):
        table.drop(op.get_bind(), checkfirst=True)
