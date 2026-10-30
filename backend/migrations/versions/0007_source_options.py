"""问题和队列保存本轮资料开关；旧记录使用兼容默认值。"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("messages", "queued_questions"):
        # 0001 从当前 ORM 建空库，首次安装可能已包含新字段；旧库则需要补齐。
        columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}
        if "source_options_json" not in columns:
            op.add_column(
                table,
                sa.Column("source_options_json", sa.Text(), nullable=False, server_default="{}"),
            )


def downgrade():
    for table in ("queued_questions", "messages"):
        op.drop_column(table, "source_options_json")
