"""把已有台账作用域保留为独立耗时项目，动作及分类原件不变。"""

import sqlalchemy as sa
from alembic import op

from app.core.identifiers import now_iso
from app.infrastructure.database.registry import Base

revision = "0024"
down_revision = "0023"
branch_labels = depends_on = None


def upgrade():
    connection = op.get_bind()
    table = Base.metadata.tables["action_timing_projects"]
    table.create(connection, checkfirst=True)
    scopes = connection.execute(
        sa.text(
            "SELECT scope_id FROM action_timing_categories "
            "UNION SELECT scope_id FROM action_timing_actions"
        )
    ).scalars()
    projects = {
        row["id"]: row
        for row in connection.execute(sa.text("SELECT id, owner_id, name FROM projects")).mappings()
    }
    owners = set(connection.execute(sa.text("SELECT id FROM accounts")).scalars())
    existing = set(connection.execute(sa.select(table.c.id)).scalars())
    for scope in list(scopes):
        if scope in existing:
            continue
        project = projects.get(scope)
        owner = project["owner_id"] if project else None
        name = project["name"] if project else "智芯2200"
        if scope.startswith("independent-") and scope[len("independent-") :] in owners:
            owner = scope[len("independent-") :]
        if name == "ZX2200 软件分析":
            name = "智芯2200"
        stamp = now_iso()
        # ID仅保留旧数据定位，不建立外键，聊天重命名、归档及删除不再影响台账。
        connection.execute(
            table.insert().values(
                id=scope, owner_id=owner, name=name, version=1, created_at=stamp, updated_at=stamp
            )
        )


def downgrade():
    op.drop_table("action_timing_projects")
