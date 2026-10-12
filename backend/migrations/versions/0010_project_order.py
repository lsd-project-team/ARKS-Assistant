"""Persist project order without changing directory or conversation identities."""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    if "sort_order" not in {row["name"] for row in sa.inspect(bind).get_columns("projects")}:
        op.add_column(
            "projects", sa.Column("sort_order", sa.Integer, nullable=False, server_default="0")
        )
        rows = bind.execute(
            sa.text("SELECT id FROM projects ORDER BY updated_at DESC, id")
        ).fetchall()
        for index, row in enumerate(rows):
            bind.execute(
                sa.text("UPDATE projects SET sort_order=:position WHERE id=:id"),
                {"position": index, "id": row[0]},
            )


def downgrade():
    op.drop_column("projects", "sort_order")
