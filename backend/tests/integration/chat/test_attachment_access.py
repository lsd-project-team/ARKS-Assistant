"""附件归属、跨项目移动及旧库迁移，使用真实登录和临时数据库。"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.main import create_app
from tests.helpers.accounts import login_second, sign_in


@pytest.mark.authentication
def test_upload_authentication_ownership_and_moved_thread(services, monkeypatch):
    monkeypatch.setattr("app.modules.chat.runs.RunManager.start", lambda *args: None)
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        first = client.post("/api/projects", json={"name": "甲项目"}).json()["id"]
        second = client.post("/api/projects", json={"name": "乙项目"}).json()["id"]
        base, target = f"/api/p/{first}", f"/api/p/{second}"
        attachment = client.post(
            base + "/attachments?filename=requirement.md", content=b"NewValue = 7"
        ).json()
        identifier = attachment["id"]
        assert client.get(target + f"/attachments/{identifier}").status_code == 404
        failed = client.post(
            target + "/threads/start", json={"content": "修改", "attachment_ids": [identifier]}
        )
        assert failed.status_code == 404
        assert client.get(target + "/threads").json() == []
        run = client.post(
            base + "/threads/start", json={"content": "修改", "attachment_ids": [identifier]}
        ).json()
        moved = client.post(
            "/api/projects/move-threads", json={"ids": [run["thread_id"]], "project_id": second}
        )
        # 移动前仍有活动运行；完成后使用原接口移动。
        assert moved.status_code == 409
        client.app.state.projects.services(first).repository.finish(run["id"], "完成")
        moved = client.post(
            "/api/projects/move-threads", json={"ids": [run["thread_id"]], "project_id": second}
        )
        assert moved.status_code == 200, moved.text
        assert "NewValue = 7" in client.get(target + f"/attachments/{identifier}").json()["content"]
        assert client.delete(target + f"/attachments/{identifier}").status_code == 409
        sign_in(client, "admin")
        client.post(
            "/api/admin/accounts",
            json={
                "username": "second",
                "display_name": "乙",
                "role": "user",
                "password": "second-pass-123456",
            },
        ).raise_for_status()
        login_second(client)
        for method, suffix in [("GET", ""), ("GET", "/download"), ("DELETE", "")]:
            assert (
                client.request(method, target + f"/attachments/{identifier}" + suffix).status_code
                == 404
            )
        own = client.get("/api/projects").json()["default_project_id"]
        assert client.get(f"/api/p/{own}/attachments/{identifier}").status_code == 404
        client.cookies.clear()
        assert (
            client.post(base + "/attachments?filename=test.md", content=b"hello").status_code == 401
        )


def test_upgrade_from_0029_preserves_questions_queue_and_adds_empty_attachments(services):
    _, database, _, repository, *_ = services
    run = repository.create_run(None, "原始问题", [])
    repository.finish(run["id"], "原始回答")
    queued = repository.queue.add(run["thread_id"], "待发问题", [])
    with database.engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE chat_attachments")
        for table in ("messages", "queued_questions"):
            connection.exec_driver_sql(f"ALTER TABLE {table} DROP COLUMN attachments_json")
        before = {
            table: list(connection.execute(text(f'SELECT * FROM "{table}"')).mappings())
            for table in inspect(connection).get_table_names()
            if table != "alembic_version"
        }
    config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    config.attributes["connection"] = database.engine
    command.stamp(config, "0029")
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with database.engine.connect() as connection:
        for table, rows in before.items():
            current = [
                dict(row) for row in connection.execute(text(f'SELECT * FROM "{table}"')).mappings()
            ]
            for row in current:
                if "attachments_json" in row:
                    assert row.pop("attachments_json") == "[]"
            assert current == rows
        assert connection.scalar(text("SELECT COUNT(*) FROM chat_attachments")) == 0
        assert not list(connection.exec_driver_sql("PRAGMA foreign_key_check"))
    assert repository.message(run["message_id"])["attachments"] == []
    assert repository.queue.list(run["thread_id"])["items"][0]["id"] == queued["id"]
