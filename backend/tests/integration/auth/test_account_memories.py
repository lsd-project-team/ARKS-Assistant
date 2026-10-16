"""个人偏好的 API、历史、运行快照及异步队列不能串账号。"""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth.context import request_identity
from app.modules.chat.runs import RunManager
from app.modules.chat.schemas import MemoryWrite
from app.modules.memory.identity import user_memory_owner
from tests.helpers.accounts import sign_in

pytestmark = pytest.mark.authentication


def test_personal_memory_api_history_restore_and_shared_project(services):
    services[4].save(MemoryWrite(name="旧公共偏好.md", content="旧的公共偏好", scope="user"))
    with TestClient(create_app(services[0])) as client:
        first = sign_in(client, "user").json()["user"]
        project = client.post("/api/projects", json={"name": "账号私有项目"}).json()
        prefix = f"/api/p/{project['id']}"
        assert not client.get(prefix + "/memories").json()
        body = {"name": "回答偏好.md", "content": "个人标记：甲只要简短回答", "scope": "user"}
        saved = client.put(prefix + "/memories", json=body)
        assert saved.status_code == 200, saved.text
        history = client.get(prefix + "/memories/user/回答偏好.md/history").json()
        assert len(history) == 1
        shared = client.put(
            prefix + "/memories",
            json={"name": "项目事实.md", "content": "项目共用事实", "scope": "project"},
        )
        assert shared.status_code == 200
        sign_in(client, "admin")
        rows = client.get(prefix + "/memories").json()
        assert [row["name"] for row in rows] == ["项目事实.md"]
        assert client.get(prefix + "/memories/user/回答偏好.md/history").json() == []
        assert (
            client.post(
                prefix + "/memories/user/回答偏好.md/restore",
                json={"revision_id": history[0]["id"]},
            ).status_code
            == 404
        )
        second = client.put(
            prefix + "/memories", json={**body, "content": "个人标记：乙要详细回答"}
        )
        assert second.status_code == 200
        assert (
            client.delete(
                prefix + "/memories/user/回答偏好.md", params={"version": second.json()["version"]}
            ).status_code
            == 200
        )
        sign_in(client, "user")
        rows = client.get(prefix + "/memories?include_deleted=true").json()
        assert "乙要详细" not in json.dumps(rows, ensure_ascii=False)
        own = next(row for row in rows if row["scope"] == "user")
        assert own["owner_id"] == first["id"] and own["content"] == body["content"]
        assert (services[0].memories / "user" / "旧公共偏好.md").exists()


def test_run_sources_events_and_trace_hide_another_accounts_private_memory(services, monkeypatch):
    with TestClient(create_app(services[0])) as client:
        user = sign_in(client, "user").json()["user"]
        project = client.post("/api/projects", json={"name": "账号私有项目"}).json()
        prefix = f"/api/p/{project['id']}"
        monkeypatch.setattr(RunManager, "start", lambda *_: None)
        run = client.post(prefix + "/threads/start", json={"content": "测试"}).json()
        repository = client.app.state.projects.services(project["id"]).repository
        repository.event(
            run["id"],
            "context_sources",
            {
                "memories": [
                    {
                        "scope": "user",
                        "owner_id": user["id"],
                        "name": "私人.md",
                        "content": "PRIVATE-MEMORY",
                    }
                ],
                "materials": [],
            },
        )
        repository.event(
            run["id"],
            "tool_start",
            {
                "name": "remember",
                "id": "call",
                "arguments": {"scope": "user", "content": "PRIVATE-TOOL"},
            },
        )
        repository.event(
            run["id"], "tool_end", {"name": "remember", "id": "call", "result": "PRIVATE-RESULT"}
        )
        repository.event(
            run["id"], "memory_save", {"name": "PRIVATE-NAME", "scope": "user", "status": "saved"}
        )
        repository.finish(run["id"], "公开的回答")
        assert "PRIVATE-MEMORY" in client.get(f"{prefix}/runs/{run['id']}/context").text
        sign_in(client, "admin")
        for suffix in ("context", "trace", "events"):
            response = client.get(f"{prefix}/runs/{run['id']}/{suffix}")
            assert response.status_code == 200
            assert "PRIVATE-" not in response.text, response.text


async def test_queue_execution_uses_question_submitter_not_dispatcher(services):
    repository, memory = services[3], services[4]
    token = request_identity.set({"user": {"id": "second", "role": "user"}})
    try:
        memory.save(MemoryWrite(name="偏好.md", content="第二人的偏好", scope="user"))
        run = repository.create_run(None, "排队的问题", [])
    finally:
        request_identity.reset(token)
    observed = []

    class Runtime:
        async def execute(self, *_):
            observed.append((user_memory_owner(), memory.prompt_snapshot("偏好")[0]))
            return "完成"

    manager = RunManager(repository, Runtime(), services[5])
    token = request_identity.set({"user": {"id": "first", "role": "admin"}})
    try:
        manager.start(run)
        await asyncio.gather(*manager.tasks.values())
    finally:
        request_identity.reset(token)
    assert observed[0][0] == "second"
    assert "第二人的偏好" in observed[0][1]
