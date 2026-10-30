import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from app.modules.chat.context import ConversationContext
from app.modules.chat.schemas import SummaryCorrection
from tests.helpers.memories import MemorySeed as MemoryWrite
from tests.helpers.memories import seed_memory
from tests.helpers.models import DeterministicModel


async def test_regenerate_keeps_original_question_and_reply_versions(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings()))
    calls = []

    def generate(_self, messages, *_args, **_kwargs):
        from langchain_core.outputs import ChatGeneration, ChatResult

        calls.append(messages)
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=f"回复版本{len(calls)}"))]
        )

    monkeypatch.setattr(DeterministicModel, "_generate", generate)
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: DeterministicModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("重新生成")
    selection = {
        "path": "Program.cs",
        "start_line": 1,
        "end_line": 2,
        "content": "独立选区快照",
        "version": "a" * 64,
    }
    original = repository.create_run(thread["id"], "解释选区", [selection])
    repository.finish(original["id"], await runtime.execute(original, lambda *_event: None))
    old_answer = repository.run(original["id"])["answer"]
    regenerated = repository.regenerate(original["id"])
    assert regenerated["message_id"] == original["message_id"]
    with pytest.raises(ValueError):
        repository.regenerate(original["id"])
    repository.finish(regenerated["id"], await runtime.execute(regenerated, lambda *_event: None))
    instruction = next(
        message for message in calls[-1] if (message.id or "").startswith("regenerate:")
    )
    assert "独立选区快照" in instruction.text
    assert instruction.text.startswith("请重新回答")
    assert old_answer not in "".join(message.text for message in calls[-1])
    conversation = repository.thread(thread["id"])
    assert [message["role"] for message in conversation["messages"]] == [
        "user",
        "assistant",
        "assistant",
    ]
    assert {run["response_message_id"] for run in conversation["runs"]} == {
        message["id"] for message in conversation["messages"] if message["role"] == "assistant"
    }
    repository.set_status(regenerated["id"], "completed")
    # 完成回复后的增量检查点也必须还原消息，不能只读当前节点变化的通道。
    context = await ConversationContext(runtime).read(thread["id"])
    assert context["message_count"] == 3
    assert context["tokens"] > 0


@pytest.mark.parametrize("failure_stage", ["before_graph", "during_generation"])
async def test_resumed_regeneration_keeps_version_link_and_one_instruction(
    services, monkeypatch, failure_stage
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings()))
    calls = []
    should_fail = False

    def generate(_self, messages, *_args, **_kwargs):
        from langchain_core.outputs import ChatGeneration, ChatResult

        if should_fail and failure_stage == "during_generation":
            raise ConnectionError("验收连接中断")
        calls.append(messages)
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=f"版本{len(calls)}"))]
        )

    def model(*_args, **_kwargs):
        if should_fail and failure_stage == "before_graph":
            raise ConnectionError("验收连接中断")
        return DeterministicModel()

    monkeypatch.setattr(DeterministicModel, "_generate", generate)
    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", model)
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("重新生成恢复")
    original = repository.create_run(thread["id"], "原始问题", [])
    repository.finish(original["id"], await runtime.execute(original, lambda *_event: None))
    regenerated = repository.regenerate(original["id"])
    should_fail = True
    with pytest.raises(ConnectionError):
        await runtime.execute(regenerated, lambda *_event: None)
    repository.set_status(regenerated["id"], "failed", "验收连接中断")
    resumed = repository.resume(regenerated["id"])
    assert resumed["regenerated_from"] == original["id"]
    should_fail = False
    answer = await runtime.execute(resumed, lambda *_event: None)
    assert answer == "版本2"
    repository.finish(resumed["id"], answer)
    assert sum((message.id or "").startswith("regenerate:") for message in calls[-1]) == 1
    assert [message["content"] for message in repository.thread(thread["id"])["messages"]] == [
        "原始问题",
        "版本1",
        "版本2",
    ]


async def test_summary_correction_changes_actual_context_without_model_call(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings()))
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: DeterministicModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    context = ConversationContext(runtime)
    thread = repository.create_thread("摘要纠错")
    run = repository.create_run(thread["id"], "原始问题必须保留", [])
    question = repository.message(run["message_id"])
    repository.finish(run["id"], "历史回复")
    config = {"configurable": {"thread_id": thread["id"]}}
    async with AsyncSqliteSaver.from_conn_string(context.checkpoints) as saver:
        graph = await runtime.graph(thread["id"], saver, lambda *_event: None)
        await graph.aupdate_state(
            config,
            {
                "messages": [
                    HumanMessage(content=question["content"], id=question["id"]),
                    AIMessage(content="历史回复"),
                ],
                "_summarization_event": {
                    "summary_message": HumanMessage(content="旧摘要"),
                    "cutoff_index": 1,
                },
            },
            as_node="model",
        )
    snapshot = await context.read(thread["id"])
    monkeypatch.setattr(
        DeterministicModel,
        "_generate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("纠错不应调用模型")),
    )
    corrected = await context.correct(
        thread["id"], SummaryCorrection(summary="用户纠正后的事实", version=snapshot["version"])
    )
    assert corrected["summary"] == "用户纠正后的事实"
    assert corrected["version"] != snapshot["version"]
    with pytest.raises(ValueError, match="变化"):
        await context.correct(
            thread["id"], SummaryCorrection(summary="过期编辑", version=snapshot["version"])
        )
    assert repository.thread(thread["id"])["messages"][0]["content"] == "原始问题必须保留"
    queued = repository.create_run(thread["id"], "新问题", [])
    with pytest.raises(ValueError, match="等待"):
        await context.correct(
            thread["id"], SummaryCorrection(summary="运行中编辑", version=corrected["version"])
        )
    seen = []

    def capture(_self, messages, *_args, **_kwargs):
        from langchain_core.outputs import ChatGeneration, ChatResult

        seen.extend(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="继续回答"))])

    monkeypatch.setattr(DeterministicModel, "_generate", capture)
    await runtime.execute(queued, lambda *_event: None)
    assert any(message.text == "用户纠正后的事实" for message in seen)
    final = await context.read(thread["id"])
    assert final["summary"] == "用户纠正后的事实"
    assert final["message_count"] > 2


def test_run_memory_snapshot_is_exact_and_survives_later_edits(services):
    paths, _, workspace, repository, memories, settings = services
    thread = repository.create_thread("记忆快照")
    saved = seed_memory(
        memories, MemoryWrite(name="偏好.md", scope="user", content="当时的回答偏好")
    )
    prompt, snapshot = memories.prompt_snapshot("回答偏好")
    assert "当时的回答偏好" in prompt
    run = repository.create_run(thread["id"], "问题", [])
    repository.event(run["id"], "context_sources", {"memories": snapshot})
    seed_memory(
        memories,
        MemoryWrite(
            name="偏好.md", scope="user", content="后来修改的偏好", version=saved["version"]
        ),
    )
    recorded = ConversationContext(
        AgentRuntime(paths, settings, workspace, repository, memories)
    ).run_sources(run["id"])
    assert recorded["recorded"]
    assert "当时的回答偏好" in recorded["memories"][0]["content"]
    seed_memory(memories, MemoryWrite(name="长记忆.md", content="长内容" * 12000))
    prompt, snapshot = memories.prompt_snapshot("偏好")
    assert len(prompt) <= 24000
    assert any(memory["partial"] for memory in snapshot)
    assert "\n\n".join(memory["injected_text"] for memory in snapshot) == prompt
