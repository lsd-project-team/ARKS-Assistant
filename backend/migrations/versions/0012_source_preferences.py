"""默认知识来源按项目保存，原始问题和队列的来源快照不变。"""

from alembic import op

from app.models import Base

revision = "0012"
down_revision = "0011"
branch_labels = depends_on = None


def upgrade():
    Base.metadata.tables["source_preferences"].create(op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table("source_preferences")
