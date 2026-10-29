"""移除数据库项目说明、指令及旧问答快照中的对应值。"""

import json

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.exec_driver_sql("PRAGMA secure_delete=ON")
    # 只删除项目设置的两个键，保留源码身份、账号及其他历史运行配置。
    runs = sa.table("runs", sa.column("id"), sa.column("project_snapshot_json"))
    for row in bind.execute(sa.select(runs.c.id, runs.c.project_snapshot_json)).mappings():
        snapshot = json.loads(row["project_snapshot_json"])
        if not isinstance(snapshot, dict):
            raise ValueError("历史项目快照格式无效，未完成项目指令清理")
        if "description" not in snapshot and "instructions" not in snapshot:
            continue
        snapshot.pop("description", None)
        snapshot.pop("instructions", None)
        bind.execute(
            runs.update()
            .where(runs.c.id == row["id"])
            .values(project_snapshot_json=json.dumps(snapshot, ensure_ascii=False))
        )
    columns = {column["name"] for column in sa.inspect(bind).get_columns("projects")}
    # 新建库可能已按当前ORM建表；SQLite原生删列避免重建被其他表引用的项目表。
    for name in ("description", "instructions"):
        if name in columns:
            op.drop_column("projects", name)


def downgrade():
    # 回退只恢复空字段，已按用户要求删除的内容不能重新出现。
    for name in ("description", "instructions"):
        op.add_column("projects", sa.Column(name, sa.Text, nullable=False, server_default=""))
