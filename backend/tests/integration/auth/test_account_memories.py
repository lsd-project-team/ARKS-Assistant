"""个人偏好的 API、历史、运行快照及异步队列不能串账号。"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth.context import request_identity
from app.modules.chat.runs import RunManager
from app.modules.memory.identity import user_memory_owner
from tests.helpers.accounts import sign_in
from tests.helpers.memories import MemorySeed as MemoryWrite
from tests.helpers.memories import seed_memory

pytestmark = pytest.mark.authentication


def test_generated_memory_is_private_even_in_a_shared_project(services):
    with TestClient(create_app(services[0])) as client:
        first = sign_in(client, "user").json()["user"]
        project = client.post("/api/projects", json={"name": "账号私有项目"}).json()
        prefix = f"/api/p/{project['id']}"
        memories = client.app.state.projects.services(project["id"]).memories
        token = request_identity.set({"user": first})
        try:
            seed_memory(
                memories, MemoryWrite(name="回答偏好.md", content="甲只要简短回答", scope="user")
            )
        finally:
            request_identity.reset(token)
        own = client.get(prefix + "/memories").json()
        assert len(own) == 1 and "甲只要简短回答" in own[0]["content"]
        sign_in(client, "admin")
        assert client.get(prefix + "/memories").json() == []
        assert client.put(prefix + "/memories", json={"content": "不能手写"}).status_code == 405
        sign_in(client, "user")
        assert client.get(prefix + "/memories").json()[0]["owner_id"] == first["id"]


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
        seed_memory(memory, MemoryWrite(name="偏好.md", content="第二人的偏好", scope="user"))
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
