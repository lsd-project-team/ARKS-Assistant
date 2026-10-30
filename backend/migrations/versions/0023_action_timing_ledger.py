"""用户维护的动作耗时台账；不迁移或生成源码模拟数据。"""

from alembic import op

from app.infrastructure.database.registry import Base

revision = "0023"
down_revision = "0022"
branch_labels = depends_on = None


def upgrade():
    for name in ("action_timing_categories", "action_timing_actions"):
        Base.metadata.tables[name].create(op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table("action_timing_actions")
    op.drop_table("action_timing_categories")
