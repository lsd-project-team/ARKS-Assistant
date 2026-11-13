"""记录最近对话的手动排序位置。"""

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = depends_on = None


def upgrade():
    connection = op.get_bind()
    columns = {column["name"] for column in sa.inspect(connection).get_columns("threads")}
    if "sort_order" not in columns:
        op.add_column("threads", sa.Column("sort_order", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("threads") as batch:
        batch.drop_column("sort_order")
