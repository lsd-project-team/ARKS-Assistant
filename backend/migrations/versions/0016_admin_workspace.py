"""管理员统计、审计和逐条提问身份；历史身份保持未知。"""

import sqlalchemy as sa
from alembic import op

from app.modules.admin.models import (
    AdminEvent,
    BusinessSubmission,
    CollectionState,
    UsageActivity,
    UsageVisit,
)

revision = "0016"
down_revision = "0015"
branch_labels = depends_on = None


def upgrade():
    for table in ("messages", "queued_questions"):
        columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}
        if "actor_id" not in columns:
            op.add_column(table, sa.Column("actor_id", sa.String(36), nullable=True))
            op.create_index(f"ix_{table}_actor_id", table, ["actor_id"])
        if "actor_json" not in columns:
            op.add_column(
                table, sa.Column("actor_json", sa.Text(), nullable=False, server_default="{}")
            )
    for model in (CollectionState, UsageVisit, UsageActivity, BusinessSubmission, AdminEvent):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in (AdminEvent, BusinessSubmission, UsageActivity, UsageVisit, CollectionState):
        model.__table__.drop(op.get_bind(), checkfirst=True)
    for table in ("messages", "queued_questions"):
        op.drop_index(f"ix_{table}_actor_id", table)
        with op.batch_alter_table(table) as batch:
            batch.drop_column("actor_id")
            batch.drop_column("actor_json")
