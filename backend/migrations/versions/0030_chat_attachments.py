"""聊天附件与消息绑定；旧问题和队列默认为无附件。"""

import sqlalchemy as sa
from alembic import op

from app.infrastructure.database.registry import Base

revision = "0030"
down_revision = "0029"
branch_labels = depends_on = None


def upgrade():
    connection = op.get_bind()
    for name in ("messages", "queued_questions"):
        columns = {row["name"] for row in sa.inspect(connection).get_columns(name)}
        if "attachments_json" not in columns:
            op.add_column(
                name, sa.Column("attachments_json", sa.Text(), nullable=False, server_default="[]")
            )
    Base.metadata.tables["chat_attachments"].create(connection, checkfirst=True)


def downgrade():
    op.drop_table("chat_attachments")
    for name in ("messages", "queued_questions"):
        op.drop_column(name, "attachments_json")
