"""真实旧表升级：归属迁移不改正文，不把后续使用者当成创建者。"""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_old_tables_upgrade_preserves_records_and_only_uses_first_actor(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.sqlite3').as_posix()}")
    migration_path = Path(__file__).parents[1] / "migrations/versions/0018_workspace_owners.py"
    spec = importlib.util.spec_from_file_location("owners_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        for statement in (
            "CREATE TABLE projects (id TEXT PRIMARY KEY, state TEXT, name TEXT)",
            "CREATE TABLE accounts (id TEXT PRIMARY KEY)",
            "CREATE TABLE threads (id TEXT PRIMARY KEY, workspace_id TEXT, state TEXT, "
            "origin_thread_id TEXT)",
            "CREATE TABLE messages (id TEXT PRIMARY KEY, thread_id TEXT, role TEXT, "
            "actor_id TEXT, content TEXT, created_at TEXT)",
            "INSERT INTO projects VALUES ('legacy','active','原项目')",
            "INSERT INTO accounts VALUES ('first'),('second')",
            "INSERT INTO threads VALUES ('known','legacy','active',NULL),"
            "('unknown','legacy','active',NULL),('branch','legacy','active','known'),"
            "('empty','legacy','deleted',NULL)",
            "INSERT INTO messages VALUES ('one','known','user','first','原始问题','1'),"
            "('two','known','user','second','后来问题','2'),"
            "('three','unknown','user',NULL,'旧消息','1'),"
            "('four','unknown','user','second','后来接着问','2')",
        ):
            connection.execute(text(statement))
        before = connection.execute(text("SELECT * FROM messages ORDER BY id")).all()
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        owners = dict(connection.execute(text("SELECT id,owner_id FROM threads")).all())
        assert owners == {"known": "first", "unknown": None, "branch": "first", "empty": None}
        assert connection.execute(text("SELECT * FROM messages ORDER BY id")).all() == before
        assert connection.execute(text("SELECT owner_id FROM projects")).scalar() is None
        assert "ix_projects_owner_state" in {
            row["name"] for row in inspect(connection).get_indexes("projects")
        }
        # 升级工具重复执行也不覆盖已确认归属。
        connection.execute(text("UPDATE threads SET owner_id='second' WHERE id='known'"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert (
            connection.execute(text("SELECT owner_id FROM threads WHERE id='known'")).scalar()
            == "second"
        )
    engine.dispose()
