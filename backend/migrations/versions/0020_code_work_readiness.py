"""执行配置、需求验收与项目预算；保留原有业务记录及验证历史。"""

import sqlalchemy as sa
from alembic import op

from app.infrastructure.database.registry import Base

revision = "0020"
down_revision = "0019"
branch_labels = depends_on = None

COLUMNS = {
    "code_changes": [
        ("requirements_json", sa.Text(), "{}"),
        ("review_json", sa.Text(), "{}"),
        ("delivered_at", sa.String(40), ""),
    ],
    "code_verification_profiles": [
        ("executor_json", sa.Text(), '{"kind":"trusted_host"}'),
        ("baseline_required", sa.Boolean(), "0"),
        ("category", sa.String(20), "build"),
        ("environment_label", sa.String(200), ""),
    ],
    "code_verifications": [
        ("purpose", sa.String(20), "change"),
        ("executor_json", sa.Text(), '{"kind":"trusted_host"}'),
        ("source_version", sa.String(64), ""),
        ("profile_version", sa.String(64), ""),
        ("error_category", sa.String(30), ""),
    ],
}


def upgrade():
    connection = op.get_bind()
    for table, columns in COLUMNS.items():
        existing = {row["name"] for row in sa.inspect(connection).get_columns(table)}
        for name, kind, default in columns:
            if name not in existing:
                op.add_column(table, sa.Column(name, kind, nullable=False, server_default=default))
    for name in ("code_work_policies", "code_work_usage", "code_work_reservations"):
        Base.metadata.tables[name].create(connection, checkfirst=True)


def downgrade():
    for name in ("code_work_reservations", "code_work_usage", "code_work_policies"):
        op.drop_table(name)
    for table, columns in reversed(list(COLUMNS.items())):
        with op.batch_alter_table(table) as batch:
            for name, _, _ in reversed(columns):
                batch.drop_column(name)
