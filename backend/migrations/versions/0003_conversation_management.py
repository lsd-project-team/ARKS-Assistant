"""会话回收站、归档、置顶、已读状态与分支来源。"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

COLUMNS = [
    sa.Column("state", sa.String(20), nullable=False, server_default="active"),
    sa.Column("deleted_at", sa.String(40), nullable=True),
    sa.Column("pinned_order", sa.Integer(), nullable=True),
    sa.Column("last_read_at", sa.String(40), nullable=True),
    sa.Column("auto_title", sa.Boolean(), nullable=False, server_default="1"),
    sa.Column("origin_thread_id", sa.String(36), nullable=True),
    sa.Column("origin_message_id", sa.String(36), nullable=True),
]


def upgrade():
    connection = op.get_bind()
    existing = {column["name"] for column in sa.inspect(connection).get_columns("threads")}
    for column in COLUMNS:
        if column.name not in existing:
            op.add_column("threads", column)
    # 旧档案在完整会话上补关联一次，避免分页后按局部顺序匹配到另一轮回复。
    threads = connection.execute(sa.text("SELECT id FROM threads")).scalars().all()
    for thread_id in threads:
        parameters = {"thread_id": thread_id}
        runs = connection.execute(
            sa.text(
                "SELECT id, response_message_id FROM runs WHERE thread_id=:thread_id "
                "AND status='completed' ORDER BY created_at, id"
            ),
            parameters,
        ).all()
        answers = (
            connection.execute(
                sa.text(
                    "SELECT id FROM messages WHERE thread_id=:thread_id AND role='assistant' "
                    "ORDER BY created_at, id"
                ),
                parameters,
            )
            .scalars()
            .all()
        )
        for run, answer in zip(runs, answers, strict=False):
            if not run.response_message_id:
                connection.execute(
                    sa.text("UPDATE runs SET response_message_id=:answer WHERE id=:id"),
                    {"id": run.id, "answer": answer},
                )


def downgrade():
    for column in reversed(COLUMNS):
        op.drop_column("threads", column.name)
