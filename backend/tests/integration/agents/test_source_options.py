"""资料开关随问题保存；排队、编辑、分支与恢复不能绕过本轮选择。"""

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from app.modules.chat.context import ConversationContext
from app.modules.chat.schemas import RunCreate, SourceOptions, SourcePreferencesWrite
from tests.helpers.api_paths import project_api
from tests.helpers.memories import MemorySeed as MemoryWrite
from tests.helpers.memories import seed_memory
from tests.helpers.models import DeterministicModel

LOCAL = {"use_deepwiki": False, "use_knowledge": False, "use_memory": False}


def test_queue_edit_branch_and_regenerate_preserve_sources(services):
    _, _, _, repository, *_ = services
    thread = repository.create_thread("来源控制")
    run = repository.create_run(thread["id"], "第一问", [], LOCAL)
    repository.finish(run["id"], "第一答")
    edited = repository.branches.edit_latest(thread["id"], run["message_id"], "改第一问", [])
    assert repository.message(edited["message_id"])["source_options"] == LOCAL
    repository.finish(edited["id"], "新回答")
    branch = repository.branches.fork(thread["id"], edited["message_id"])
    assert repository.thread(branch["id"])["messages"][0]["source_options"] == LOCAL
    item = repository.queue.add(thread["id"], "第二问", [], LOCAL)
    item = repository.queue.update(item["id"], "编辑第二问", [], item["updated_at"])
    assert item["source_options"] == LOCAL
    queued = repository.queue.dispatch(thread["id"])
    assert repository.message(queued["message_id"])["source_options"] == LOCAL
    repository.finish(queued["id"], "第二答")
    regenerated = repository.regenerate(queued["id"])
    assert repository.message(regenerated["message_id"])["source_options"] == LOCAL


async def test_disabled_sources_do_not_connect_mcp_or_inject_memory(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=16384, output_tokens=512)))
    seed_memory(
        memories, MemoryWrite(name="偏好.md", scope="user", content="仅供来源隔离测试的记忆事实")
    )
    tools, prompts = [], []

    class Model(DeterministicModel):
        def bind_tools(self, supplied, **_kwargs):
            tools.extend(item.name for item in supplied)
            return self

        def _generate(self, messages, *args, **kwargs):
            prompts.extend(message.text for message in messages)
            return super()._generate(messages, *args, **kwargs)

    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_args, **_kwargs: Model()
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)

    async def forbidden(*_args):
        raise AssertionError("来源开关关闭时不能连接 MCP")

    monkeypatch.setattr(runtime, "remote_tools", forbidden)
    run = repository.create_run(None, "你好", [], LOCAL)
    answer = await runtime.execute(
        run, lambda kind, payload: repository.event(run["id"], kind, payload)
    )
    assert answer == "测试回复"
    assert (
        "read_source" in tools
        and "remember" not in tools
        and "search_project_knowledge" not in tools
    )
    assert "仅供来源隔离测试的记忆事实" not in "\n".join(prompts)
    snapshot = ConversationContext(runtime).run_sources(run["id"])
    assert snapshot["source_options"] == LOCAL and snapshot["memories"] == []
    assert snapshot["budget"]["breakdown"]["memory"] == 0


def test_legacy_requests_keep_compatible_defaults():
    request = RunCreate(content="你好")
    assert request.source_options is None
    assert SourceOptions.model_validate({}).model_dump() == {key: True for key in LOCAL}


def test_project_defaults_are_captured_without_changing_saved_questions(services):
    repository = services[3]
    preferences = repository.source_preferences
    assert preferences.get() == {"source_options": SourceOptions().model_dump(), "version": 0}
    preferences.save(SourcePreferencesWrite(source_options=SourceOptions(**LOCAL), version=0))
    first = repository.create_run(None, "新问题使用项目默认值", [])
    repository.finish(first["id"], "第一答")
    queued = repository.queue.add(first["thread_id"], "已排队问题", [])
    preferences.save(SourcePreferencesWrite(source_options=SourceOptions(), version=1))
    assert repository.message(first["message_id"])["source_options"] == LOCAL
    assert queued["source_options"] == LOCAL
    dispatched = repository.queue.dispatch(first["thread_id"])
    assert repository.message(dispatched["message_id"])["source_options"] == LOCAL
    repository.finish(dispatched["id"], "队列回答")
    regenerated = repository.regenerate(dispatched["id"])
    assert repository.message(regenerated["message_id"])["source_options"] == LOCAL
    repository.finish(regenerated["id"], "重生成回答")
    edited = repository.branches.edit_latest(
        first["thread_id"], dispatched["message_id"], "只修改文字", []
    )
    assert repository.message(edited["message_id"])["source_options"] == LOCAL
    repository.finish(edited["id"], "编辑回答")
    new = repository.create_run(first["thread_id"], "后续新问题", [])
    assert repository.message(new["message_id"])["source_options"] == SourceOptions().model_dump()


def test_source_preferences_scope_restart_and_stale_save(services):
    from fastapi.testclient import TestClient

    from app.main import create_app

    paths = services[0]
    with TestClient(create_app(paths)) as client:
        project = client.post(
            "/api/projects", json={"name": "来源隔离", "source_root": str(paths.workspace)}
        ).json()
        endpoint = f"/api/p/{project['id']}/source-options"
        defaults = client.get(endpoint).json()
        assert defaults["version"] == 0
        changed = client.put(endpoint, json={"source_options": LOCAL, "version": 0})
        assert changed.status_code == 200 and changed.json()["version"] == 1
        assert client.put(endpoint, json={"source_options": LOCAL, "version": 0}).status_code == 409
        stale = {"source_options": SourceOptions().model_dump(), "version": 9}
        assert client.put(endpoint, json=stale).status_code == 409
        assert (
            client.get(project_api(client, "/source-options")).json()["source_options"]
            == defaults["source_options"]
        )
        independent = "/api/p/independent/source-options"
        assert client.get(independent).json()["source_options"] == defaults["source_options"]
        memory_only = {**LOCAL, "use_memory": True}
        assert (
            client.put(independent, json={"source_options": memory_only, "version": 0}).status_code
            == 200
        )
    with TestClient(create_app(paths)) as client:
        assert client.get(endpoint).json() == {"source_options": LOCAL, "version": 1}
        assert client.get(independent).json()["source_options"] == memory_only


def test_legacy_question_keeps_empty_source_snapshot_after_preferences_change(services):
    repository = services[3]
    old = repository.create_run(None, "旧问题", [], {})
    repository.finish(old["id"], "旧答")
    repository.source_preferences.save(
        SourcePreferencesWrite(source_options=SourceOptions(**LOCAL), version=0)
    )
    regenerated = repository.regenerate(old["id"])
    assert repository.message(regenerated["message_id"])["source_options"] == {}
