"""从已有0022数据库升级，旧记录不变且新台账为空。"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select

from app.infrastructure.database.registry import Base
from app.infrastructure.database.session import Database
from app.modules.action_timing.models import TimingAction, TimingCategory, TimingRun
from app.modules.auth.models import Account


def test_ledger_migration_preserves_legacy_data_and_is_idempotent(tmp_path):
    database = Database(tmp_path / "legacy.sqlite3")
    new_tables = {"action_timing_categories", "action_timing_actions"}
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
