"""交接工作台只增加自己的四张表。"""

from alembic import op

from app.handover import models  # noqa: F401
from app.models import Base

revision = "0013"
down_revision = "0012"
branch_labels = depends_on = None

TABLES = ("handover_records", "handover_revisions", "handover_blobs", "handover_events")


def upgrade():
    for name in TABLES:
        Base.metadata.tables[name].create(op.get_bind(), checkfirst=True)


def downgrade():
    for name in reversed(TABLES):
        op.drop_table(name)
