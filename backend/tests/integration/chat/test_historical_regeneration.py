"""历史重答追加、末条版本、隔离上下文与恢复均使用真实数据库和图状态。"""

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.runtime.engine import AgentRuntime
from app.agents.tools.engineering import engineering_tools
from app.core.config import AppSettings, ModelSettings
from app.main import create_app
from app.modules.chat.context import ConversationContext
from app.modules.chat.lifecycle import ConversationLifecycle
from app.modules.chat.models import Thread
from app.modules.chat.regeneration import CONTEXT_EVENT, previous_run_event
from app.modules.chat.runs import RunManager
from app.modules.code_changes.request_binding import RequestOrigin
from app.modules.projects.models import Project
from tests.helpers.models import DeterministicModel

SOURCES = {"use_memory": False, "use_knowledge": False, "use_deepwiki": False}


def answered(repository, thread_id, question, answer):
    run = repository.create_run(thread_id, question, [], SOURCES)
    repository.finish(run["id"], answer)
    return repository.run(run["id"])


@pytest.fixture
def model_runtime(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings(), mcp_servers=[]))
    calls = []

    def generate(_self, messages, *_args, **_kwargs):
        calls.append(messages)
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=f"验收回答{len(calls)}"))]
        )

    monkeypatch.setattr(DeterministicModel, "_generate", generate)
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_a, **_kw: DeterministicModel()
    )
    return AgentRuntime(paths, settings, workspace, repository, memories), calls


async def execute(repository, runtime, run):
    answer = await runtime.execute(
        run, lambda kind, payload: repository.event(run["id"], kind, payload)
    )
    repository.finish(run["id"], answer)
    return repository.run(run["id"])


async def test_historical_append_preserves_later_context_then_latest_versions_stay_together(
    services, model_runtime
):
    repository = services[3]
    runtime, calls = model_runtime
    thread = repository.create_thread("历史重答")
    for question in ("背景问题X", "原题A", "后续问题B"):
        run = repository.create_run(thread["id"], question, [], SOURCES)
        await execute(repository, runtime, run)
    original = repository.thread(thread["id"])
    source = original["runs"][1]
    original_checkpoint = runtime.checkpoint_id(thread["id"])
    appended = repository.regenerate(source["id"])
    assert appended["thread_id"] == thread["id"]
    assert appended["message_id"] != source["message_id"]
    assert appended["regenerated_from"] == source["id"]
    await execute(repository, runtime, appended)
    prompt = "\n".join(message.text for message in calls[-1])
    assert all(text in prompt for text in ("背景问题X", "验收回答1", "原题A"))
    assert all(text not in prompt for text in ("后续问题B", "验收回答2", "验收回答3"))
    conversation = repository.thread(thread["id"])
    assert conversation["messages"][:6] == original["messages"]
    assert conversation["messages"][-2]["reanswered_from"] == source["message_id"]
    assert conversation["messages"][-1]["content"] == "验收回答4"
    assert len(repository.threads()) == 1
    async with AsyncSqliteSaver.from_conn_string(
        str(runtime.paths.data / "checkpoints.sqlite3")
    ) as saver:
        graph = await runtime.graph(thread["id"], saver, lambda *_: None, inspection=True)
        state = await graph.aget_state({"configurable": {"thread_id": original_checkpoint}})
        assert state.values["messages"][-1].text == "验收回答3"

    # 查看待重建的主会话不写检查点；其后切换版本，下一轮仍须读取最新答案。
    assert (await ConversationContext(runtime).read(thread["id"]))["message_count"] == 8
    async with AsyncSqliteSaver.from_conn_string(
        str(runtime.paths.data / "checkpoints.sqlite3")
    ) as saver:
        assert (
            await saver.aget_tuple(
                {"configurable": {"thread_id": runtime.checkpoint_id(thread["id"])}}
            )
            is None
        )
    latest = repository.regenerate(appended["id"])
    assert latest["message_id"] == appended["message_id"]
    await execute(repository, runtime, latest)
    assert "验收回答4" not in "\n".join(message.text for message in calls[-1])
    archive = repository.thread(thread["id"])
    assert len(archive["messages"]) == 9
    assert archive["messages"][-2]["content"] == "验收回答4"
    assert archive["messages"][-1]["content"] == "验收回答5"
    followup = repository.create_run(thread["id"], "继续讨论整个会话", [], SOURCES)
    await execute(repository, runtime, followup)
    prompt = "\n".join(message.text for message in calls[-1])
    assert all(
        text in prompt for text in ("原题A", "后续问题B", "验收回答2", "验收回答3", "验收回答5")
    )
    assert "验收回答4" not in prompt


async def test_latest_regeneration_without_checkpoint_keeps_preceding_answer(
    services, model_runtime
):
    repository = services[3]
    runtime, calls = model_runtime
    thread = repository.create_thread("冷恢复末条")
    answered(repository, thread["id"], "较早问题", "必须保留的较早答案")
    last = answered(repository, thread["id"], "末条问题", "应被替换的末条答案")
    regenerated = repository.regenerate(last["id"])
    assert regenerated["message_id"] == last["message_id"]
    await execute(repository, runtime, regenerated)
    prompt = "\n".join(message.text for message in calls[-1])
    assert "必须保留的较早答案" in prompt
    assert "应被替换的末条答案" not in prompt


async def test_historical_code_request_reuses_original_copy_and_contract(
    services, model_runtime, monkeypatch
):
    repository = services[3]
    runtime, _ = model_runtime
    repository.project_id = repository.workspace_id
    with repository.database.session.begin() as session:
        session.add(
            Project(
                id=repository.project_id,
                name="重答代码请求",
                source_root=str(runtime.workspace.root),
            )
        )
    request = "请修复Program.cs入口，只允许修改Program.cs"
    original = answered(repository, None, request, "原代码建议")
    changes = runtime.code_changes
    first = changes.create(
        "入口修改",
        "修复入口",
        acceptance_criteria=["入口仍存在"],
        constraints="不得改测试",
        allowed_paths=["Program.cs"],
        request_origin=RequestOrigin(
            "chat", request, message_id=original["message_id"], run_id=original["id"]
        ),
    )
    loaded = changes.read_file(first["id"], "Program.cs")
    changes.edit_file(first["id"], "Program.cs", "Main", "Start", loaded["version"])
    answered(repository, original["thread_id"], "后续普通问题", "后续普通答案")
    regenerated = repository.regenerate(original["id"])

    class ReachedCodeTool(Exception):
        pass

    async def inspect_graph(*_args, **kwargs):
        tools = {
            item.name: item
            for item in engineering_tools(
                runtime, kwargs["question_text"], evidence=kwargs["evidence"]
            )
        }
        result = json.loads(
            await tools["create_code_change"].ainvoke(
                {
                    "title": "重答时的创建尝试",
                    "goal": "修复入口",
                    "acceptance_criteria": [],
                    "allowed_paths": [],
                }
            )
        )
        assert result["id"] == first["id"] and result["reused"] is True
        assert result["acceptance_criteria"] == ["入口仍存在"]
        assert result["constraints"] == "不得改测试"
        assert result["allowed_paths"] == ["Program.cs"]
        assert "Start" in changes.read_file(first["id"], "Program.cs")["content"]
        assert len(changes.list()) == 1
        raise ReachedCodeTool

    monkeypatch.setattr(runtime, "graph", inspect_graph)
    with pytest.raises(ReachedCodeTool):
        await runtime.execute(regenerated, lambda *_: None)


async def test_regenerating_completed_version_after_a_failed_attempt_stays_in_same_group(
    services, model_runtime, monkeypatch
):
    repository = services[3]
    runtime, calls = model_runtime
    original = repository.create_run(None, "末条原题A", [], SOURCES)
    await execute(repository, runtime, original)
    failed = repository.regenerate(original["id"])
    original_generate = DeterministicModel._generate

    def failure(*_a, **_kw):
        raise ConnectionError("工具或模型中断")

    monkeypatch.setattr(DeterministicModel, "_generate", failure)
    with pytest.raises(ConnectionError):
        await runtime.execute(failed, lambda *_: None)
    repository.set_status(failed["id"], "failed")
    monkeypatch.setattr(DeterministicModel, "_generate", original_generate)
    retry = repository.regenerate(original["id"])
    assert retry["message_id"] == original["message_id"]
    await execute(repository, runtime, retry)
    assert "验收回答1" not in "\n".join(message.text for message in calls[-1])
    archive = repository.thread(original["thread_id"])
    assert len(archive["messages"]) == 3
    assert archive["messages"][-1]["content"] == "验收回答2"


@pytest.mark.parametrize("failure_stage", ["before_graph", "during_generation"])
async def test_historical_regeneration_resume_reuses_request_and_isolated_checkpoint(
    services, model_runtime, monkeypatch, failure_stage
):
    repository = services[3]
    runtime, calls = model_runtime
    thread = repository.create_thread("重答恢复")
    first = answered(repository, thread["id"], "原题A", "原答案A")
    answered(repository, thread["id"], "后续问题B", "后续答案B")
    appended = repository.regenerate(first["id"])
    original_graph, original_generate = runtime.graph, DeterministicModel._generate

    def failure(*_a, **_kw):
        raise ConnectionError("重答验收中断")

    monkeypatch.setattr(
        runtime if failure_stage == "before_graph" else DeterministicModel,
        "graph" if failure_stage == "before_graph" else "_generate",
        failure,
    )
    with pytest.raises(ConnectionError):
        await runtime.execute(appended, lambda *_: None)
    repository.set_status(appended["id"], "failed", "验收中断")
    resumed = repository.resume(appended["id"])
    assert resumed["message_id"] == appended["message_id"]
    assert repository.run_event(resumed["id"], CONTEXT_EVENT) == repository.run_event(
        appended["id"], CONTEXT_EVENT
    )
    monkeypatch.setattr(runtime, "graph", original_graph)
    monkeypatch.setattr(DeterministicModel, "_generate", original_generate)
    await execute(repository, runtime, resumed)
    instructions = [message for message in calls[-1] if message.id == appended["message_id"]]
    assert len(instructions) == 1 and "原题A" in instructions[0].text
    assert "后续问题B" not in "\n".join(message.text for message in calls[-1])
    assert len(repository.thread(thread["id"])["messages"]) == 6


def test_historical_append_copies_exact_selections_sources_and_root_when_repeated(services):
    repository = services[3]
    thread = repository.create_thread("重答来源")
    selection = {"path": "Program.cs", "content": "原选区", "version": "a" * 64}
    first = repository.create_run(thread["id"], "原题", [selection], SOURCES)
    repository.finish(first["id"], "原答案")
    answered(repository, thread["id"], "后来的问题", "后来的答案")
    appended = repository.regenerate(first["id"])
    question = repository.message(appended["message_id"])
    assert question["selections"] == [selection]
    assert question["source_options"] == SOURCES
    assert (
        question["source_workspace_id"]
        == repository.message(first["message_id"])["source_workspace_id"]
    )
    repository.finish(appended["id"], "第一次重答")
    answered(repository, thread["id"], "另一个新问题", "另一个答案")
    repeated = repository.regenerate(appended["id"])
    assert repository.message(repeated["message_id"])["origin_message_id"] == first["message_id"]
    assert (
        repository.run_event(repeated["id"], CONTEXT_EVENT)["before_message_id"]
        == first["message_id"]
    )
    assert len(repository.thread(thread["id"])["messages"]) == 9


@pytest.mark.parametrize("blocked", ["busy", "creation_guard", "incomplete", "source_changed"])
def test_historical_regeneration_rejects_invalid_state_without_creating_messages(services, blocked):
    repository = services[3]
    thread = repository.create_thread("重答保护")
    first = answered(repository, thread["id"], "原题A", "原答案A")
    next_run = repository.create_run(thread["id"], "后续问题B", [], SOURCES)
    if blocked != "busy":
        repository.finish(next_run["id"], "后续答案B")
    if blocked == "creation_guard":

        def forbidden():
            raise ValueError("项目已归档")

        repository.creation_guard = forbidden
    elif blocked == "incomplete":
        repository.set_status(first["id"], "failed")
    elif blocked == "source_changed":
        repository.source_workspace_id = "other-source"
    before = repository.thread(thread["id"])
    with pytest.raises(ValueError):
        repository.regenerate(first["id"])
    after = repository.thread(thread["id"])
    assert after["messages"] == before["messages"]
    assert after["runs"] == before["runs"]
    assert after["context_generation"] == before["context_generation"]


def test_historical_regeneration_api_appends_then_groups_latest_without_new_thread(
    services, monkeypatch
):
    monkeypatch.setattr(RunManager, "start", lambda *_: None)
    app = create_app(services[0])
    with TestClient(app) as client:
        project_id = app.state.projects.default_id
        repository = app.state.projects.services(project_id).repository
        first = answered(repository, None, "原题A", "原答案A")
        answered(repository, first["thread_id"], "后续问题B", "后续答案B")
        prefix = f"/api/p/{project_id}"
        response = client.post(prefix + f"/runs/{first['id']}/regenerate")
        assert response.status_code == 201
        appended = response.json()
        assert appended["thread_id"] == first["thread_id"]
        assert appended["message_id"] != first["message_id"]
        assert client.post(prefix + f"/runs/{first['id']}/regenerate").status_code == 409
        repository.finish(appended["id"], "新的原题A答案")
        refreshed = client.get(prefix + f"/threads/{first['thread_id']}").json()
        assert [row["content"] for row in refreshed["messages"]] == [
            "原题A",
            "原答案A",
            "后续问题B",
            "后续答案B",
            "原题A",
            "新的原题A答案",
        ]
        assert refreshed["messages"][-2]["reanswered_from"] == first["message_id"]
        latest = client.post(prefix + f"/runs/{appended['id']}/regenerate")
        assert latest.status_code == 201
        assert latest.json()["message_id"] == appended["message_id"]


def test_old_followup_without_own_plan_does_not_reuse_later_questions_plan(services):
    repository = services[3]
    first = answered(repository, None, "原任务A", "原任务答案")
    repository.event(first["id"], "analysis_plan", {"question": "原任务A"})
    continued = answered(repository, first["thread_id"], "继续", "当时的继续答案")
    later = answered(repository, first["thread_id"], "不同任务B", "不同任务答案")
    repository.event(later["id"], "analysis_plan", {"question": "不同任务B"})
    regenerated = repository.regenerate(continued["id"])
    assert previous_run_event(repository, regenerated, "analysis_plan") == {"question": "原任务A"}


def test_latest_group_uses_latest_checkpoint_but_project_context_invalidation_refreshes_it(
    services,
):
    repository = services[3]
    first = answered(repository, None, "原题A", "原答案A")
    answered(repository, first["thread_id"], "后续问题B", "后续答案B")
    appended = repository.regenerate(first["id"])
    repository.finish(appended["id"], "重答第一版")
    second = repository.regenerate(appended["id"])
    repository.finish(second["id"], "重答第二版")
    third = repository.regenerate(appended["id"])
    repository.finish(third["id"], "从旧版本再次生成")
    first_context = repository.run_event(appended["id"], CONTEXT_EVENT)
    assert (
        repository.run_event(third["id"], CONTEXT_EVENT)["generation"]
        == first_context["generation"]
    )
    with repository.database.session.begin() as session:
        session.get(Thread, first["thread_id"]).context_generation += 1
    refreshed = repository.regenerate(third["id"])
    assert refreshed["message_id"] == appended["message_id"]
    assert (
        repository.run_event(refreshed["id"], CONTEXT_EVENT)["generation"]
        != first_context["generation"]
    )


def test_reanswer_label_survives_pagination_when_original_question_is_not_loaded(services):
    repository = services[3]
    first = answered(repository, None, "最早原题A", "最早答案A")
    for index in range(42):
        answered(repository, first["thread_id"], f"后续问题{index}", f"后续答案{index}")
    regenerated = repository.regenerate(first["id"])
    repository.finish(regenerated["id"], "新的A答案")
    page = repository.thread(first["thread_id"], limit=80)
    assert first["message_id"] not in {row["id"] for row in page["messages"]}
    assert page["messages"][-2]["reanswered_from"] == first["message_id"]


async def test_purge_removes_historical_regeneration_and_normal_context_checkpoints(
    services, model_runtime
):
    repository = services[3]
    runtime, _ = model_runtime
    first = answered(repository, None, "原题A", "原答案A")
    answered(repository, first["thread_id"], "后续问题B", "后续答案B")
    regenerated = repository.regenerate(first["id"])
    await execute(repository, runtime, regenerated)
    await ConversationContext(runtime).read(first["thread_id"])
    followup = repository.create_run(first["thread_id"], "后续问题C", [], SOURCES)
    await execute(repository, runtime, followup)
    repository.catalog.change(first["thread_id"], "deleted")
    await ConversationLifecycle(SimpleNamespace(paths=runtime.paths, repository=repository)).purge(
        first["thread_id"]
    )
    async with AsyncSqliteSaver.from_conn_string(
        str(runtime.paths.data / "checkpoints.sqlite3")
    ) as saver:
        for generation in (1, 2):
            config = {"configurable": {"thread_id": f"{first['thread_id']}:project:{generation}"}}
            assert [saved async for saved in saver.alist(config)] == []
