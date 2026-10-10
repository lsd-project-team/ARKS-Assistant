"""问题编辑、分支、等待发送队列与运行阶段。"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

COLUMNS = {
    "threads": [sa.Column("queue_paused", sa.Boolean(), nullable=False, server_default="0")],
    "messages": [
        sa.Column("context_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("replaces_id", sa.String(36), nullable=True),
        sa.Column("origin_message_id", sa.String(36), nullable=True),
    ],
    "runs": [
        sa.Column("reset_context", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("stage", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("error_code", sa.String(40), nullable=False, server_default=""),
        sa.Column("started_at", sa.String(40), nullable=True),
        sa.Column("finished_at", sa.String(40), nullable=True),
    ],
}


def upgrade():
    connection = op.get_bind()
    for table, columns in COLUMNS.items():
        existing = {column["name"] for column in sa.inspect(connection).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)
    if "queued_questions" not in sa.inspect(connection).get_table_names():
        op.create_table(
            "queued_questions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "thread_id",
                sa.String(36),
                sa.ForeignKey("threads.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("selections_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.Column("updated_at", sa.String(40), nullable=False),
        )
        op.create_index("ix_queued_questions_thread_id", "queued_questions", ["thread_id"])
    connection.execute(
        sa.text("UPDATE runs SET stage=status WHERE status NOT IN ('running','queued')")
    )


def downgrade():
    op.drop_table("queued_questions")
    for table, columns in reversed(COLUMNS.items()):
        for column in reversed(columns):
            op.drop_column(table, column.name)
