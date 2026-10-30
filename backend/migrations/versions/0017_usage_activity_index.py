"""活动时间按账号查询最近记录，兼容已开始采集的数据库。"""

from alembic import op
from sqlalchemy import inspect

revision = "0017"
down_revision = "0016"
branch_labels = depends_on = None


def upgrade():
    indexes = {item["name"] for item in inspect(op.get_bind()).get_indexes("usage_activity")}
    if "ix_usage_activity_account_time" not in indexes:
        op.create_index(
            "ix_usage_activity_account_time", "usage_activity", ["account_id", "created_at"]
        )


def downgrade():
    op.drop_index("ix_usage_activity_account_time", "usage_activity")
