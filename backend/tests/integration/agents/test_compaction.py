from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from tests.helpers.models import DeterministicModel


async def test_native_compaction_archives_and_preserves_original(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=8192, output_tokens=512)))
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: DeterministicModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("压缩回归")
    history = []
    for index in range(6):
        run = repository.create_run(thread["id"], f"原始问题{index}" + "原始上下文" * 400, [])
        message = repository.message(run["message_id"])
        history.extend(
            [
                HumanMessage(content=message["content"], id=message["id"]),
                AIMessage(content="原始回答" * 400),
            ]
        )
        repository.finish(run["id"], "原始回答" * 400)
    config = {"configurable": {"thread_id": thread["id"]}}
    events = []
    async with AsyncSqliteSaver.from_conn_string(str(paths.data / "checkpoints.sqlite3")) as saver:
        graph = await runtime.graph(thread["id"], saver, lambda *event: events.append(event))
        await graph.aupdate_state(config, {"messages": history}, as_node="model")
    new_run = repository.create_run(thread["id"], "继续", [])
    answer = await runtime.execute(new_run, lambda *event: events.append(event))
    assert answer == "测试回复"
    assert any(kind == "stage" and payload["stage"] == "compacting" for kind, payload in events)
    archives = list(paths.scratch.rglob("*.md"))
    assert archives, "原生压缩应产生可恢复的对话档案"
    assert any("原始问题0" in file.read_text(encoding="utf-8") for file in archives)
    original = repository.thread(thread["id"])["messages"]
    assert len(original) == 13
    assert "原始问题0" in original[0]["content"]
