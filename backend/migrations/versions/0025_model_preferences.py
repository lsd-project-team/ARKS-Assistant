"""为现有账号增加个人模型选择，保留系统默认配置和业务记录。"""

from alembic import op

from app.infrastructure.database.registry import Base

revision = "0025"
down_revision = "0024"
branch_labels = depends_on = None


def upgrade():
    Base.metadata.tables["model_preferences"].create(op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table("model_preferences")
