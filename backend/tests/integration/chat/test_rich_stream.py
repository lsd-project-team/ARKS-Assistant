import asyncio
import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from app.modules.chat.runs import RunManager
from tests.helpers.models import DeterministicModel

ANSWER = (
    "开头文字\n\n```rich-content\n"
    + json.dumps(
        {
            "version": 1,
            "blocks": [
                {
                    "id": "s",
                    "type": "step_flow",
                    "steps": [{"id": "a", "title": "检查条件", "description": "按已核对流程执行"}],
                }
            ],
        },
        ensure_ascii=False,
    )
    + "\n```\n\n结束文字"
)


async def test_rich_content_uses_existing_tokens_replay_and_history(services):
    class Runtime:
        async def execute(self, _run, emit):
            for offset in range(0, len(ANSWER), 7):
                emit("token", {"text": ANSWER[offset : offset + 7]})
            return ANSWER

    repository, settings = services[3], services[5]
    manager = RunManager(repository, Runtime(), settings)
    run = repository.create_run(None, "测试结构化流", [])
    manager.start(run)
    await manager.tasks[run["id"]]
    events = repository.events(run["id"])
    assert "".join(row["payload"]["text"] for row in events if row["kind"] == "token") == ANSWER
    assert events[-1]["payload"]["answer"] == ANSWER
    cursor = events[len(events) // 2]["sequence"]
    replay = [row async for row in manager.stream(run["id"], cursor)]
    assert replay[0]["sequence"] == cursor + 1
    thread = repository.thread(run["thread_id"])
    assert thread["messages"][-1]["content"] == ANSWER
    assert thread["runs"][-1]["answer"] == ANSWER


@pytest.mark.parametrize("status", ["cancelled", "failed"])
async def test_partial_rich_block_retained_and_retry_uses_same_question(services, status):
    ready = asyncio.Event()
    partial = ANSWER[:70]

    class Runtime:
        async def execute(self, _run, emit):
            emit("token", {"text": partial})
            ready.set()
            if status == "failed":
                raise ValueError("模拟提供商失败")
            await asyncio.Event().wait()

    repository, settings = services[3], services[5]
    manager = RunManager(repository, Runtime(), settings)
    run = repository.create_run(None, "保留中断内容", [])
    manager.start(run)
    task = manager.tasks[run["id"]]
    await ready.wait()
    if status == "cancelled":
        await manager.cancel(run["id"])
    await task
    saved = repository.run(run["id"])
    assert saved["answer"] == partial and saved["status"] == status
    assert repository.events(run["id"])[-1]["payload"]["status"] == status
    retried = repository.resume(run["id"])
    assert retried["message_id"] == run["message_id"]
    assert len(repository.thread(run["thread_id"])["messages"]) == 1


async def test_actual_agent_graph_reads_source_and_checks_structured_answer(services, monkeypatch):
    answer = (
        "入口在 Main。\n\n```rich-content\n"
        + json.dumps(
            {
                "version": 1,
                "blocks": [
                    {
                        "id": "flow",
                        "type": "step_flow",
                        "steps": [
                            {
                                "id": "entry",
                                "title": "入口方法",
                                "description": "Main 方法体为空。",
                                "sources": [{"path": "Program.cs", "start_line": 2, "end_line": 2}],
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n```"
    )

    class StructuredModel(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if "独立的源码结论复核器" in messages[0].text:
                payload = json.loads(messages[-1].text)
                assert "rich-content" not in payload["answer"]
                assert "Main 方法体为空" in payload["answer"]
                assert any(row["path"] == "Program.cs" for row in payload["source"])
                result = AIMessage(
                    content='{"verdict":"passed","issues":[],"reason":"测试替身复核"}'
                )
            elif any(
                isinstance(row, ToolMessage) and row.name == "read_source" for row in messages
            ):
                result = AIMessage(content=answer)
            else:
                assert "可选展示协议" in messages[0].text
                result = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "read-entry",
                            "name": "read_source",
                            "args": {"path": "Program.cs", "start_line": 2, "end_line": 2},
                        }
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=result)])

    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=16384, output_tokens=1024)))
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_args, **_kwargs: StructuredModel()
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    run = repository.create_run(None, "解释 Program.cs 的入口方法", [])
    actual = await runtime.execute(
        run, lambda kind, payload: repository.event(run["id"], kind, payload)
    )
    assert actual == answer
    validation = repository.run_event(run["id"], "answer_validation")
    assert validation["passed"] and validation["citations"][0]["start_line"] == 2
    assert repository.run_event(run["id"], "source_review")["verdict"] == "passed"
