"""首批动作耗时批次与原始事件。"""

from alembic import op

from app.infrastructure.database.registry import Base

revision = "0022"
down_revision = "0021"
branch_labels = depends_on = None


def upgrade():
    for name in ("action_timing_runs", "action_timing_samples"):
        Base.metadata.tables[name].create(op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table("action_timing_samples")
    op.drop_table("action_timing_runs")
