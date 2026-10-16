"""配置草稿、凭据隔离和并发修改都经过公开 API 验证。"""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.agents.runtime.configuration import current_configuration
from app.core.config import SECRET_MASK, AppSettings, ModelProfile, ModelSettings
from app.main import create_app
from app.modules.chat.runs import RunManager
from tests.helpers.api_paths import project_api


def profiles():
    return AppSettings(
        active_profile_id="first",
        model_profiles=[
            ModelProfile(
                id="first",
                name="主模型",
                config=ModelSettings(
                    base_url="https://first.invalid/v1", model="first-model", api_key="first-secret"
                ),
            ),
            ModelProfile(
                id="second",
                name="备用模型",
                config=ModelSettings(
                    base_url="https://second.invalid/v1",
                    model="second-model",
                    api_key="second-secret",
                ),
            ),
        ],
    )


def draft(client):
    value = client.get("/api/settings").json()
    version = value.pop("version")
    value.pop("model")
    return {"settings": value, "version": version}


def test_profile_secrets_clear_and_stale_window_are_isolated(services):
    paths, *_, store = services
    store.save(profiles())
    with TestClient(create_app(paths)) as client:
        body = draft(client)
        assert "first-secret" not in json.dumps(body)
        assert "second-secret" not in json.dumps(body)
        body["settings"]["active_profile_id"] = "second"
        body["settings"]["model_profiles"].append({"id": "new", "name": "新模型", "config": {}})
        response = client.put("/api/settings", json=body)
        assert response.status_code == 200
        stored = {row.id: row.config.api_key for row in store.load().model_profiles}
        assert stored == {"first": "first-secret", "second": "second-secret", "new": ""}
        assert store.load().model.model == "second-model"
        assert client.put("/api/settings", json=body).status_code == 409
        fresh = draft(client)
        fresh["clear_profile_keys"] = ["first"]
        assert client.put("/api/settings", json=fresh).status_code == 200
        assert store.load().model_profiles[0].config.api_key == ""
        assert store.load().model_profiles[1].config.api_key == "second-secret"
        fresh = draft(client)
        fresh["settings"]["model_profiles"] = fresh["settings"]["model_profiles"][1:]
        assert client.put("/api/settings", json=fresh).status_code == 200
        assert "first" not in {row.id for row in store.load().model_profiles}


def test_legacy_profile_migration_and_probe_cache_recovery(services):
    store = services[-1]
    store.path.write_text(
        json.dumps(
            {
                "model": {
                    "base_url": "https://legacy.invalid/v1",
                    "model": "legacy",
                    "api_key": "legacy-secret",
                }
            }
        ),
        encoding="utf-8",
    )
    public = store.public()
    assert public["active_profile_id"] == "default"
    assert public["model_profiles"][0]["config"]["has_api_key"]
    config = AppSettings.model_validate(public)
    store.save(config)
    assert store.load().model.api_key == "legacy-secret"
    probe_file = store.path.with_name("model-probes.json")
    for malformed in ("{broken", "[]", '{"default": null}'):
        probe_file.write_text(malformed, encoding="utf-8")
        assert store.public()["model"]["has_api_key"]


@pytest.mark.parametrize(
    "payload",
    [
        {"model": {}, "model_profiles": [None]},
        {"model": {}, "model_profiles": [{}]},
        {"model_profiles": [{"id": "a", "name": " ", "config": {}}]},
        {
            "mcp_servers": [
                {
                    "id": "wiki",
                    "name": "Wiki",
                    "url": "https://wiki.invalid/mcp",
                    "headers": {"Bad Header": "DO-NOT-ECHO"},
                }
            ]
        },
        {
            "mcp_servers": [
                {
                    "id": "wiki",
                    "name": "Wiki",
                    "url": "https://wiki.invalid/mcp",
                    "headers": {"Authorization": "DO-NOT-ECHO\nother"},
                }
            ]
        },
        {
            "mcp_servers": [
                {
                    "id": "wiki",
                    "name": "Wiki",
                    "url": "https://wiki.invalid/mcp",
                    "env": {"2BAD": "DO-NOT-ECHO"},
                }
            ]
        },
    ],
)
def test_malformed_settings_are_validation_errors_without_credentials(services, payload):
    with TestClient(create_app(services[0])) as client:
        response = client.put("/api/settings", json={"settings": payload})
        assert response.status_code == 422
        assert "DO-NOT-ECHO" not in response.text


def test_probes_use_drafts_without_saving_and_invalidate_old_results(services, monkeypatch):
    paths, *_, store = services
    store.save(profiles())
    seen = []

    async def check(config):
        seen.append(config.model_copy())
        return {"ok": True, "checks": [], "model": config.model}

    monkeypatch.setattr("app.modules.settings.router.probe_capabilities", check)
    with TestClient(create_app(paths)) as client:
        before = store.path.read_bytes()
        body = draft(client)
        body["profile_id"] = "second"
        body["settings"]["model_profiles"][1]["config"]["model"] = "unsaved-model"
        assert client.post("/api/settings/probe", json=body).status_code == 200
        assert seen[0].model == "unsaved-model" and seen[0].api_key == "second-secret"
        assert store.path.read_bytes() == before
        assert "capabilities" not in store.public()["model_profiles"][1]
        assert client.put("/api/settings", json=body).status_code == 200
        assert store.public()["model_profiles"][1]["capabilities"]["ok"]
        body = draft(client)
        body["settings"]["model_profiles"][1]["config"]["temperature"] = 0.7
        assert client.put("/api/settings", json=body).status_code == 200
        assert "capabilities" not in store.public()["model_profiles"][1]
        assert "second-secret" not in store.path.with_name("model-probes.json").read_text()


def test_mcp_draft_preserves_only_matching_credentials_and_reports_errors(services, monkeypatch):
    paths, *_, store = services
    store.save(
        AppSettings(
            mcp_servers=[
                {
                    "id": "wiki",
                    "name": "Wiki",
                    "url": "https://wiki.invalid/mcp",
                    "headers": {"Authorization": "mcp-secret"},
                }
            ]
        )
    )
    seen = []

    async def check(server):
        seen.append(server.model_copy())
        if "unavailable" in server.url:
            raise RuntimeError("mcp-secret")
        return {"name": server.name, "tools": [{"name": "read_docs", "schema": {}}]}

    monkeypatch.setattr("app.modules.settings.router.probe_mcp", check)
    with TestClient(create_app(paths)) as client:
        server = store.public()["mcp_servers"][0]
        assert server["headers"]["Authorization"] == SECRET_MASK
        server["url"] = "https://draft.invalid/mcp"
        before = store.path.read_bytes()
        response = client.post("/api/mcp/wiki/probe", json={"server": server})
        assert response.status_code == 200
        assert seen[0].headers["Authorization"] == "mcp-secret"
        assert seen[0].url == "https://draft.invalid/mcp"
        assert store.path.read_bytes() == before
        server["url"] = "https://unavailable.invalid/mcp"
        failure = client.post("/api/mcp/wiki/probe", json={"server": server})
        assert failure.status_code == 502 and "mcp-secret" not in failure.text
        server["id"] = "other"
        assert client.post("/api/mcp/other/probe", json={"server": server}).status_code == 409


@pytest.mark.parametrize("fail_first", [False, True])
async def test_running_configuration_snapshot_survives_global_switch(services, fail_first):
    _, _, _, repository, _, store = services
    store.save(profiles())
    entered, release = asyncio.Event(), asyncio.Event()
    seen = []

    class Runtime:
        async def execute(self, run, _emit):
            config = current_configuration(store)
            if run["id"] == first["id"]:
                entered.set()
                await release.wait()
            seen.append((run["id"], config.model.model, config.model.api_key))
            if fail_first and run["id"] == first["id"]:

                class AuthenticationError(Exception):
                    status_code = 401

                raise AuthenticationError(f"凭据失效：{config.model.api_key}")
            return config.model.model

    manager = RunManager(repository, Runtime(), store)
    first = repository.create_run(repository.create_thread("第一轮配置验收")["id"], "第一轮", [])
    manager.start(first)
    first_task = manager.tasks[first["id"]]
    await asyncio.wait_for(entered.wait(), 2)
    config = store.load()
    config.active_profile_id = "second"
    config.model = config.model_profiles[1].config
    store.save(config)
    second = repository.create_run(repository.create_thread("第二轮配置验收")["id"], "第二轮", [])
    manager.start(second)
    second_task = manager.tasks[second["id"]]
    await asyncio.wait_for(second_task, 2)
    release.set()
    await asyncio.wait_for(first_task, 2)
    assert set(seen) == {
        (first["id"], "first-model", "first-secret"),
        (second["id"], "second-model", "second-secret"),
    }
    assert first["model_snapshot"]["profile_id"] == "first"
    assert repository.run(second["id"])["model_snapshot"]["profile_id"] == "second"
    archive = json.dumps(repository.thread(first["thread_id"]), ensure_ascii=False)
    events = json.dumps(repository.events(first["id"]), ensure_ascii=False)
    assert "first-secret" not in archive + events and "second-secret" not in archive + events
    assert repository.run(first["id"])["status"] == ("failed" if fail_first else "completed")


def test_blank_memory_write_is_rejected_and_original_preserved(services):
    with TestClient(create_app(services[0])) as client:
        memory = client.put(
            project_api(client, "/memories"), json={"name": "验收.md", "content": "原内容"}
        ).json()
        invalid = client.put(project_api(client, "/memories"), json={**memory, "content": " \n "})
        assert invalid.status_code == 409
        assert client.get(project_api(client, "/memories")).json()[0]["content"] == "原内容"
