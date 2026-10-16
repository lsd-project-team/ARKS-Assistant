"""新增管理员、普通用户与可撤销登录会话，保留全部现有业务数据。"""

from alembic import op

from app.auth.models import Account, LoginSession

revision = "0015"
down_revision = "0014"
branch_labels = depends_on = None


def upgrade():
    for model in (Account, LoginSession):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in (LoginSession, Account):
        model.__table__.drop(op.get_bind(), checkfirst=True)
