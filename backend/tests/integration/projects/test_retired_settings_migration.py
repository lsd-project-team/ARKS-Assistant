"""旧库升级清理已删除的设置，问答正文与其他业务数据保持原样。"""

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.modules.projects.models import Project


def migration_config(database):
    config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    config.attributes["connection"] = database.engine
    return config


def test_upgrade_removes_settings_and_snapshots_preserving_business_data(services):
    _, database, _, repository, *_ = services
    with database.session.begin() as session:
        for state in ("active", "archived", "deleted"):
            session.add(
                Project(id=state, name=f"原名称-{state}", state=state, deepwiki_repo="org/repo")
            )
    run = repository.create_run(None, "保留原问题", [])
    repository.finish(run["id"], "保留原答案")
    kept_snapshot = {
        "id": "active",
        "name": "原名称-active",
        "source_root": "/source",
        "_execution_user": {"id": "original-user", "display_name": "原账号"},
    }
    with database.engine.begin() as connection:
        for field in ("description", "instructions"):
            connection.exec_driver_sql(
                f"ALTER TABLE projects ADD COLUMN {field} TEXT NOT NULL DEFAULT ''"
            )
        connection.execute(text("UPDATE projects SET description='旧说明',instructions='旧指令'"))
        connection.execute(
            text("UPDATE runs SET project_snapshot_json=:snapshot WHERE id=:id"),
            {
                "id": run["id"],
                "snapshot": json.dumps(
                    {**kept_snapshot, "description": "旧说明", "instructions": "旧指令"},
                    ensure_ascii=False,
                ),
            },
        )
        before = {
            table: list(connection.execute(text(f'SELECT * FROM "{table}"')).mappings())
            for table in inspect(connection).get_table_names()
        }
    config = migration_config(database)
    command.stamp(config, "0025")
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    assert not {"description", "instructions"} & {
        column["name"] for column in inspect(database.engine).get_columns("projects")
    }
    with database.engine.connect() as connection:
        for table, original in before.items():
            expected = [dict(row) for row in original]
            for row in expected:
                if table == "projects":
                    row.pop("description")
                    row.pop("instructions")
                if table == "runs":
                    row["project_snapshot_json"] = json.dumps(kept_snapshot, ensure_ascii=False)
            assert list(connection.execute(text(f'SELECT * FROM "{table}"')).mappings()) == expected
        assert not list(connection.exec_driver_sql("PRAGMA foreign_key_check"))
    command.downgrade(config, "0025")
    with database.engine.connect() as connection:
        assert set(connection.execute(text("SELECT description,instructions FROM projects"))) == {
            ("", "")
        }
    command.upgrade(config, "head")


def test_upgrade_accepts_current_schema_without_retired_columns(services):
    database = services[1]
    config = migration_config(database)
    command.stamp(config, "0025")
    command.upgrade(config, "head")
    assert not {"description", "instructions"} & {
        column["name"] for column in inspect(database.engine).get_columns("projects")
    }
