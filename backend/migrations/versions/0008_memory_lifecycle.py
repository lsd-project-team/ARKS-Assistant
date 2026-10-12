"""Memory validity and review lifecycle, preserving legacy records as valid."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = depends_on = None


def upgrade():
    for table in ("memory_records", "memory_revisions"):
        columns = {row["name"] for row in sa.inspect(op.get_bind()).get_columns(table)}
        if "lifecycle" not in columns:
            op.add_column(
                table, sa.Column("lifecycle", sa.String(20), nullable=False, server_default="valid")
            )


def downgrade():
    for table in ("memory_records", "memory_revisions"):
        op.drop_column(table, "lifecycle")
