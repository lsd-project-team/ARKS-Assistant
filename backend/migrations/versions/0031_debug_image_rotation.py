"""为问题与经验原图保存跨版本共用的显示旋转角度。"""

import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = depends_on = None


def upgrade():
    connection = op.get_bind()
    columns = {
        column["name"] for column in sa.inspect(connection).get_columns("handover_debug_images")
    }
    if "rotation" not in columns:
        op.add_column(
            "handover_debug_images",
            sa.Column("rotation", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade():
    with op.batch_alter_table("handover_debug_images") as batch:
        batch.drop_column("rotation")
