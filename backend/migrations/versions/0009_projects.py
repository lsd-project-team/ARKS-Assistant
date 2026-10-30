"""Durable projects and original source provenance; legacy data is adopted at startup."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if "projects" not in tables:
        op.create_table(
            "projects",
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("description", sa.Text, nullable=False, server_default=""),
            sa.Column("source_root", sa.Text, nullable=True),
            sa.Column("instructions", sa.Text, nullable=False, server_default=""),
            sa.Column("deepwiki_repo", sa.String(200), nullable=False, server_default=""),
            sa.Column("state", sa.String(20), nullable=False, server_default="active"),
            sa.Column("pinned_order", sa.Integer, nullable=True),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.Column("updated_at", sa.String(40), nullable=False),
        )
    if "source_workspaces" not in tables:
        op.create_table(
            "source_workspaces",
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("root", sa.Text, nullable=False),
        )
    additions = {
        "threads": sa.Column("project_id", sa.String(32), nullable=True),
        "messages": sa.Column("source_workspace_id", sa.String(32), nullable=True),
        "runs": sa.Column("project_snapshot_json", sa.Text, nullable=False, server_default="{}"),
    }
    for table, column in additions.items():
        if column.name not in {row["name"] for row in sa.inspect(bind).get_columns(table)}:
            op.add_column(table, column)
    if "context_generation" not in {row["name"] for row in sa.inspect(bind).get_columns("threads")}:
        op.add_column(
            "threads",
            sa.Column("context_generation", sa.Integer, nullable=False, server_default="0"),
        )
    if "ix_threads_project_id" not in {
        row["name"] for row in sa.inspect(bind).get_indexes("threads")
    }:
        op.create_index("ix_threads_project_id", "threads", ["project_id"])


def downgrade():
    op.drop_index("ix_threads_project_id", table_name="threads")
    op.drop_column("runs", "project_snapshot_json")
    op.drop_column("messages", "source_workspace_id")
    op.drop_column("threads", "project_id")
    op.drop_column("threads", "context_generation")
    op.drop_table("source_workspaces")
    op.drop_table("projects")
