"""回复版本和消息关联，原始答案继续保留。"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("runs")}
    for name in ("regenerated_from", "response_message_id"):
        if name not in existing:
            op.add_column("runs", sa.Column(name, sa.String(36), nullable=True))


def downgrade():
    op.drop_column("runs", "response_message_id")
    op.drop_column("runs", "regenerated_from")
