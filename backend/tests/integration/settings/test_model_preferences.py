"""个人模型切换经过真实登录、迁移与运行快照验证，不调用外部模型。"""

import asyncio
import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agents.runtime.configuration import current_configuration
from app.core.config import AppSettings
from app.infrastructure.database.registry import Base
from app.infrastructure.database.session import Database
from app.main import create_app
from app.modules.auth.context import request_identity
from app.modules.auth.models import Account
from app.modules.chat.runs import RunManager
from app.modules.settings.model_preferences import ModelPreferences
from app.modules.settings.models import ModelPreference
from tests.helpers.accounts import sign_in

pytestmark = pytest.mark.authentication


def configured_models(store):
    store.save(
        AppSettings(
            active_profile_id="first",
            model_profiles=[
                {
                    "id": identifier,
                    "name": identifier,
                    "config": {
                        "model": f"{identifier}-model",
                        "base_url": f"https://{identifier}.invalid/v1",
                        "api_key": f"{identifier}-secret",
                    },
                }
                for identifier in ("first", "second")
            ],
        )
    )


def test_user_selection_is_private_persistent_and_cannot_edit_configuration(services):
    paths, *_, store = services
    configured_models(store)
    original = store.path.read_bytes()
    with TestClient(create_app(paths)) as client:
        assert client.get("/api/model-preference").status_code == 401
        assert client.put("/api/model-preference", json={"profile_id": "second"}).status_code == 401
        user = sign_in(client, "user").json()["user"]
        assert client.get("/api/model-preference").json()["active_profile_id"] == "first"
        bad_csrf = client.put(
            "/api/model-preference",
            json={"profile_id": "second"},
            headers={"X-Arks-CSRF": "wrong"},
        )
        assert bad_csrf.status_code == 403
        response = client.put("/api/model-preference", json={"profile_id": "second"})
        assert response.status_code == 200
        assert response.json() == {
            "active_profile_id": "second",
            "model_profiles": [
                {"id": name, "name": name, "model": f"{name}-model"} for name in ("first", "second")
            ],
        }
        assert "secret" not in response.text and "base_url" not in response.text
        for payload in (
            {"profile_id": "first", "account_id": "other"},
            {"profile_id": "first", "model": {"api_key": "DO-NOT-ECHO"}},
            {"profile_id": ""},
        ):
            invalid = client.put("/api/model-preference", json=payload)
            assert invalid.status_code == 422
            assert "DO-NOT-ECHO" not in invalid.text
        assert (
            client.put("/api/model-preference", json={"profile_id": "missing"}).status_code == 409
        )
        assert client.get("/api/model-preference").json()["active_profile_id"] == "second"
        assert client.put("/api/settings", json={"settings": {}}).status_code == 403
        assert client.post("/api/settings/probe").status_code == 403
        assert store.path.read_bytes() == original
        assert client.post("/api/auth/logout").status_code == 204
        sign_in(client)
        assert client.get("/api/model-preference").json()["active_profile_id"] == "first"
        assert client.put("/api/model-preference", json={"profile_id": "first"}).status_code == 200
        sign_in(client, "user")
        assert client.get("/api/model-preference").json()["active_profile_id"] == "second"
        with client.app.state.auth.database.session() as session:
            assert session.get(ModelPreference, user["id"]).profile_id == "second"
    # 新服务实例、重新登录仍读取数据库中的个人选择。
    with TestClient(create_app(paths)) as client:
        sign_in(client, "user")
        assert client.get("/api/model-preference").json()["active_profile_id"] == "second"
        config = store.load()
        config.model_profiles = config.model_profiles[:1]
        store.save(config)
        assert client.get("/api/model-preference").json()["active_profile_id"] == "first"
        assert client.put("/api/model-preference", json={"profile_id": "first"}).status_code == 200


async def test_user_switch_preserves_active_run_and_dispatch_uses_original_actor(services):
    _, database, _, repository, _, store = services
    configured_models(store)
    with database.session.begin() as session:
        session.add_all(
            [
                Account(
                    id=name,
                    username=name,
                    display_name=name,
                    role="admin" if name == "bob" else "user",
                    password_hash="fixture",
                )
                for name in ("alice", "bob")
            ]
        )
    preferences = ModelPreferences(database, store)
    entered, release = asyncio.Event(), asyncio.Event()
    seen = []

    class Runtime:
        async def execute(self, run, _emit):
            if run["id"] == first["id"]:
                entered.set()
                await release.wait()
            config = current_configuration(store, database)
            seen.append((run["id"], config.active_profile_id, config.model.api_key))
            return config.model.model

    manager = RunManager(repository, Runtime(), store)
    token = request_identity.set({"user": {"id": "alice", "username": "alice", "role": "user"}})
    try:
        first = repository.create_run(repository.create_thread("第一轮")["id"], "开始", [])
        manager.start(first)
        first_task = manager.tasks[first["id"]]
        await asyncio.wait_for(entered.wait(), 2)
        preferences.save("alice", "second")
        second = repository.create_run(repository.create_thread("下一轮")["id"], "继续", [])
        # 管理员可以读取其他人的对话，但后台出队仍必须使用消息保存的发起人。
        request_identity.set({"user": {"id": "bob", "username": "bob", "role": "admin"}})
        manager.start(second)
        await asyncio.wait_for(manager.tasks[second["id"]], 2)
        regenerated = repository.regenerate(second["id"])
        manager.start(regenerated)
        await asyncio.wait_for(manager.tasks[regenerated["id"]], 2)
        third = repository.create_run(repository.create_thread("其他用户")["id"], "开始", [])
        manager.start(third)
        await asyncio.wait_for(manager.tasks[third["id"]], 2)
        assert current_configuration(store, database).active_profile_id == "first"
        release.set()
        await asyncio.wait_for(first_task, 2)
        assert set(seen) == {
            (first["id"], "first", "first-secret"),
            (second["id"], "second", "second-secret"),
            (regenerated["id"], "first", "first-secret"),
            (third["id"], "first", "first-secret"),
        }
        assert second["model_snapshot"]["profile_id"] == "second"
        archive = json.dumps(repository.run(second["id"]))
        assert "secret" not in archive
        assert store.load().active_profile_id == "first"
    finally:
        release.set()
        await manager.shutdown()
        request_identity.reset(token)


def test_model_preference_migration_keeps_existing_accounts_and_default(tmp_path):
    database = Database(tmp_path / "previous.sqlite3")
    for table in Base.metadata.sorted_tables:
        if table.name != "model_preferences":
            table.create(database.engine)
    with database.session.begin() as session:
        session.add(
            Account(
                id="existing",
                username="existing",
                display_name="原账号",
                role="user",
                password_hash="fixture",
            )
        )
    config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    config.attributes["connection"] = database.engine
    command.stamp(config, "0024")
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with database.session() as session:
        assert session.get(Account, "existing").display_name == "原账号"
        assert list(session.scalars(select(ModelPreference))) == []
    database.close()
