"""问题与经验原图；保留既有记录及不可变修订。"""

from alembic import op

from app.infrastructure.database.registry import Base

revision = "0021"
down_revision = "0020"
branch_labels = depends_on = None


def upgrade():
    Base.metadata.tables["handover_debug_images"].create(op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table("handover_debug_images")
