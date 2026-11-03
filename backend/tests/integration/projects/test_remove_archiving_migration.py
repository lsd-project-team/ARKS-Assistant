"""旧归档记录恢复入口；迁移只改变状态，不丢失原文、归属或队列控制。"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.modules.chat.models import Thread
from app.modules.projects.models import Project


def test_upgrade_restores_archived_records_preserving_all_other_fields(services):
    _, database, _, repository, *_ = services
    thread = repository.create_thread("原问题标题")
    run = repository.create_run(thread["id"], "保留原问题", [{"path": "原文件.cs"}])
    repository.finish(run["id"], "保留原答案")
    queued = repository.queue.add(thread["id"], "保持暂停的问题", [])
    repository.queue.pause(thread["id"])
    deleted = repository.create_thread("仍在回收站")
    repository.catalog.change(deleted["id"], "deleted")
    with database.session.begin() as session:
        for state in ("active", "archived", "deleted"):
            session.add(
                Project(id=state, name=f"原项目-{state}", state=state, owner_id="original-owner")
            )
        original = session.get(Thread, thread["id"])
        original.state = "archived"
        original.project_id = "archived"
        original.owner_id = "original-owner"

    config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    config.attributes["connection"] = database.engine
    command.stamp(config, "0027")
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
            expected = [dict(row) for row in rows]
            for row in expected:
                if table in {"projects", "threads"} and row["state"] == "archived":
                    row["state"] = "active"
            assert list(connection.execute(text(f'SELECT * FROM "{table}"')).mappings()) == expected
        assert not list(connection.exec_driver_sql("PRAGMA foreign_key_check"))
        restored = connection.execute(
            text("SELECT state, queue_paused, owner_id FROM threads WHERE id=:id"),
            {"id": thread["id"]},
        ).one()
        assert tuple(restored) == ("active", 1, "original-owner")
        assert (
            connection.scalar(
                text("SELECT content FROM queued_questions WHERE id=:id"), {"id": queued["id"]}
            )
            == "保持暂停的问题"
        )
