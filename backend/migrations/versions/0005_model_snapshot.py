"""记录每轮实际使用的模型参数，不保存凭据。"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("runs")}
    if "model_snapshot_json" not in columns:
        op.add_column(
            "runs", sa.Column("model_snapshot_json", sa.Text(), nullable=False, server_default="{}")
        )


def downgrade():
    op.drop_column("runs", "model_snapshot_json")
