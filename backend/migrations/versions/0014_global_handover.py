"""交接资料迁移到全局，保留记录 ID、附件、版本及原始来源身份。"""

import sqlalchemy as sa
from alembic import op

from app.modules.handover.infrastructure.persistence import models as models

revision = "0014"
down_revision = "0013"
branch_labels = depends_on = None

TABLES = ("handover_records", "handover_revisions", "handover_blobs", "handover_events")


def upgrade():
    bind = op.get_bind()
    if "project_id" not in {column["name"] for column in sa.inspect(bind).get_columns(TABLES[0])}:
        # 新安装的 0013 已按当前模型建表，无需再次搬运。
        return
    temporary = sa.MetaData()
    created = {}
    for name in TABLES:
        original = models.Base.metadata.tables[name]
        columns = []
        for column in original.columns:
            foreign_keys = (
                [sa.ForeignKey("handover_records_global.id")] if column.name == "record_id" else []
            )
            columns.append(
                sa.Column(
                    column.name,
                    column.type,
                    *foreign_keys,
                    primary_key=column.primary_key,
                    nullable=column.nullable,
                )
            )
        table = sa.Table(name + "_global", temporary, *columns)
        table.create(bind)
        created[name] = table
        destination = ", ".join(column.name for column in table.columns)
        source = ", ".join(
            "project_id" if column.name == "source_project_id" else column.name
            for column in table.columns
        )
        bind.execute(
            sa.text(f"INSERT INTO {table.name} ({destination}) SELECT {source} FROM {name}")
        )
    # 先移走子表，再替换父表，始终保持外键检查启用。
    for name in reversed(TABLES):
        op.drop_table(name)
    for name in TABLES:
        op.rename_table(created[name].name, name)
        for index in models.Base.metadata.tables[name].indexes:
            index.create(bind)
    violations = bind.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError("全局交接迁移发现引用异常，请恢复升级前备份")


def downgrade():
    raise RuntimeError("全局交接新增记录无法无损还原为对话项目记录，请使用升级前备份回退")
