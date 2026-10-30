"""Frozen initial SQLite schema; independent from future application models."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS memory_records (
        id VARCHAR(250) NOT NULL,
        workspace_id VARCHAR(32) NOT NULL,
        scope VARCHAR(20) NOT NULL,
        name VARCHAR(100) NOT NULL,
        source_thread_id VARCHAR(36),
        source_paths_json TEXT NOT NULL,
        updated_at VARCHAR(40) NOT NULL,
        PRIMARY KEY (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS threads (
        id VARCHAR(36) NOT NULL,
        workspace_id VARCHAR(32) NOT NULL,
        title VARCHAR(120) NOT NULL,
        created_at VARCHAR(40) NOT NULL,
        updated_at VARCHAR(40) NOT NULL,
        PRIMARY KEY (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id VARCHAR(36) NOT NULL,
        thread_id VARCHAR(36) NOT NULL,
        role VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        selections_json TEXT NOT NULL,
        created_at VARCHAR(40) NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(thread_id) REFERENCES threads (id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS runs (
        id VARCHAR(36) NOT NULL,
        thread_id VARCHAR(36) NOT NULL,
        message_id VARCHAR(36) NOT NULL,
        status VARCHAR(20) NOT NULL,
        answer TEXT NOT NULL,
        error TEXT NOT NULL,
        resumed_from VARCHAR(36),
        created_at VARCHAR(40) NOT NULL,
        updated_at VARCHAR(40) NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(thread_id) REFERENCES threads (id) ON DELETE CASCADE,
        FOREIGN KEY(message_id) REFERENCES messages (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS run_events (
        id INTEGER NOT NULL,
        run_id VARCHAR(36) NOT NULL,
        sequence INTEGER NOT NULL,
        kind VARCHAR(40) NOT NULL,
        payload_json TEXT NOT NULL,
        created_at VARCHAR(40) NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(run_id) REFERENCES runs (id) ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_memory_records_workspace_id ON memory_records (workspace_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_threads_workspace_id ON threads (workspace_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_messages_thread_id ON messages (thread_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_runs_status ON runs (status)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_runs_thread_id ON runs (thread_id)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ix_run_event_cursor ON run_events (run_id, sequence)
    """,
)


def upgrade() -> None:
    for statement in SCHEMA:
        op.execute(statement)


def downgrade() -> None:
    for table in ("run_events", "runs", "messages", "memory_records", "threads"):
        op.drop_table(table)
