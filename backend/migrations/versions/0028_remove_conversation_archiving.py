"""移除项目与对话归档状态，恢复入口并保留内容、归属、时间与队列暂停状态。"""

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = depends_on = None


def upgrade():
    # 不改删除状态，不自动启动暂停的队列，也不改变原始更新时间和阅读顺序。
    for table in ("projects", "threads"):
        op.execute(f"UPDATE {table} SET state = 'active' WHERE state = 'archived'")


def downgrade():
    # 恢复为正常状态不丢失业务内容，不能推测哪些项目或对话原本处于归档状态。
    pass
