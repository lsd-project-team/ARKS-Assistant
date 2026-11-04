"""新增回答反馈，保留原消息和所有回答版本。"""

from alembic import op

from app.infrastructure.database.registry import Base

revision = "0029"
down_revision = "0028"
branch_labels = depends_on = None


def upgrade():
    Base.metadata.tables["answer_feedback"].create(op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table("answer_feedback")
