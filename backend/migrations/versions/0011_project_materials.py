"""Versioned project documents, confirmed conclusions and additional source roots."""

import sqlalchemy as sa
from alembic import op

from app.models import Base

revision = "0011"
down_revision = "0010"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    if "source_folders_json" not in {
        row["name"] for row in sa.inspect(bind).get_columns("projects")
    }:
        op.add_column(
            "projects",
            sa.Column("source_folders_json", sa.Text, nullable=False, server_default="[]"),
        )
    for name in ("project_materials", "project_material_revisions"):
        Base.metadata.tables[name].create(bind, checkfirst=True)


def downgrade():
    op.drop_table("project_material_revisions")
    op.drop_table("project_materials")
    op.drop_column("projects", "source_folders_json")
