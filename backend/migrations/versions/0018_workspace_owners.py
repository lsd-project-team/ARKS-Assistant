"""项目和对话归属；不能确认的旧数据保留给管理员，不默认分给新登录用户。"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = depends_on = None


def upgrade():
    connection = op.get_bind()
    for table in ("projects", "threads"):
        columns = {item["name"] for item in sa.inspect(connection).get_columns(table)}
        if "owner_id" not in columns:
            op.add_column(table, sa.Column("owner_id", sa.String(36), nullable=True))
    for table, name, columns in (
        ("projects", "ix_projects_owner_state", ["owner_id", "state"]),
        ("threads", "ix_threads_owner_workspace_state", ["owner_id", "workspace_id", "state"]),
    ):
        if name not in {item["name"] for item in sa.inspect(connection).get_indexes(table)}:
            op.create_index(name, table, columns)
    # 仅首条原始用户消息有服务端账号记录时才迁移；不能拿后续使用者冒充创建人。
    connection.execute(
        sa.text("""
        UPDATE threads SET owner_id = (
            SELECT m.actor_id FROM messages m JOIN accounts a ON a.id = m.actor_id
            WHERE m.id = (
                SELECT first.id FROM messages first
                WHERE first.thread_id = threads.id AND first.role = 'user'
                ORDER BY first.created_at, first.id LIMIT 1
            )
        ) WHERE owner_id IS NULL AND origin_thread_id IS NULL
    """)
    )
    # 分支继承原对话的归属，保留原始问答身份，绝不改写消息作者。
    for _ in range(100):
        result = connection.execute(
            sa.text("""
            UPDATE threads SET owner_id = (
                SELECT parent.owner_id FROM threads parent
                WHERE parent.id = threads.origin_thread_id
            ) WHERE owner_id IS NULL AND origin_thread_id IS NOT NULL
            AND EXISTS (SELECT 1 FROM threads parent
                WHERE parent.id = threads.origin_thread_id AND parent.owner_id IS NOT NULL)
        """)
        )
        if not result.rowcount:
            break


def downgrade():
    op.drop_index("ix_threads_owner_workspace_state", "threads")
    op.drop_index("ix_projects_owner_state", "projects")
    with op.batch_alter_table("threads") as batch:
        batch.drop_column("owner_id")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("owner_id")
