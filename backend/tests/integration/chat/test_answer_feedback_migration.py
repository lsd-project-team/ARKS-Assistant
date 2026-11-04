"""旧库升级新增反馈表，原问答和版本逐字段保留。"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text


def test_upgrade_preserves_existing_data_and_creates_feedback_indexes(services):
    _, database, _, repository, *_ = services
    run = repository.create_run(None, "保留问题", [])
    repository.finish(run["id"], "保留答案")
    with database.engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE answer_feedback")
    config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    config.attributes["connection"] = database.engine
    command.stamp(config, "0028")
    with database.engine.connect() as connection:
        before = {
            table: list(connection.execute(text(f'SELECT * FROM "{table}"')).mappings())
            for table in inspect(connection).get_table_names()
            if table != "alembic_version"
        }
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with database.engine.connect() as connection:
        for table, rows in before.items():
            assert list(connection.execute(text(f'SELECT * FROM "{table}"')).mappings()) == rows
        assert connection.scalar(text("SELECT COUNT(*) FROM answer_feedback")) == 0
        assert {row["name"] for row in inspect(connection).get_indexes("answer_feedback")} == {
            "ix_answer_feedback_thread_id",
            "ix_answer_feedback_message_id",
        }
        assert len(inspect(connection).get_foreign_keys("answer_feedback")) == 4
        assert not list(connection.exec_driver_sql("PRAGMA foreign_key_check"))
