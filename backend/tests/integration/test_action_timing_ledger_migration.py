"""从已有0022数据库升级，旧记录不变且新台账为空。"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select

from app.infrastructure.database.registry import Base
from app.infrastructure.database.session import Database
from app.modules.action_timing.models import TimingAction, TimingCategory, TimingProject, TimingRun
from app.modules.auth.models import Account
from app.modules.projects.models import Project


def test_ledger_migration_preserves_legacy_data_and_is_idempotent(tmp_path):
    database = Database(tmp_path / "legacy.sqlite3")
    new_tables = {"action_timing_categories", "action_timing_actions", "action_timing_projects"}
    for table in Base.metadata.sorted_tables:
        if table.name not in new_tables:
            table.create(database.engine)
    with database.session.begin() as session:
        session.add(
            Account(
                id="old-user",
                username="old-user",
                display_name="原账号",
                role="user",
                password_hash="non-login-fixture",
            )
        )
        session.add(
            TimingRun(
                id="old-run",
                scope_id="independent-old-user",
                source_run_id="old",
                content_hash="a" * 64,
                file_hash="b" * 64,
                manifest_json="{}",
                package_json="{}",
            )
        )
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.attributes["connection"] = database.engine
    command.stamp(config, "0022")
    assert not new_tables.intersection(inspect(database.engine).get_table_names())
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with database.session() as session:
        assert session.get(Account, "old-user").display_name == "原账号"
        assert session.get(TimingRun, "old-run").package_json == "{}"
        for model in (TimingCategory, TimingAction):
            assert session.scalar(select(func.count()).select_from(model)) == 0
    database.close()


def test_timing_project_migration_preserves_records_owners_and_chat_names(tmp_path):
    database = Database(tmp_path / "ledger.sqlite3")
    for table in Base.metadata.sorted_tables:
        if table.name != "action_timing_projects":
            table.create(database.engine)
    with database.session.begin() as session:
        session.add(
            Account(
                id="engineer",
                username="engineer",
                display_name="工程师",
                role="user",
                password_hash="fixture",
            )
        )
        session.add(Project(id="old-chat", owner_id="engineer", name="ZX2200 软件分析"))
        session.add(
            TimingCategory(id="category", scope_id="old-chat", name="固晶", name_key="固晶")
        )
        session.flush()
        session.add_all(
            [
                TimingAction(
                    id="zero",
                    scope_id="old-chat",
                    category_id="category",
                    name="零",
                    name_key="零",
                    duration_seconds=0,
                    notes="保留",
                ),
                TimingAction(
                    id="blank",
                    scope_id="independent-engineer",
                    name="未填",
                    name_key="未填",
                    duration_seconds=None,
                ),
            ]
        )
    with database.engine.connect() as connection:
        snapshots = {
            name: list(connection.execute(Base.metadata.tables[name].select()).mappings())
            for name in ("projects", "action_timing_categories", "action_timing_actions")
        }
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.attributes["connection"] = database.engine
    command.stamp(config, "0023")
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with database.engine.connect() as connection:
        for name, before in snapshots.items():
            assert (
                list(connection.execute(Base.metadata.tables[name].select()).mappings()) == before
            )
    with database.session.begin() as session:
        rows = list(session.scalars(select(TimingProject)))
        assert {(row.id, row.owner_id, row.name) for row in rows} == {
            ("old-chat", "engineer", "智芯2200"),
            ("independent-engineer", "engineer", "智芯2200"),
        }
        session.delete(session.get(Project, "old-chat"))
    with database.session() as session:
        assert session.get(TimingProject, "old-chat").name == "智芯2200"
        assert session.get(TimingAction, "zero").duration_seconds == 0
    database.close()
