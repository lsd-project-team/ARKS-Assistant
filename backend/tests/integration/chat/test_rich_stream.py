import asyncio
import json

import pytest

from app.modules.chat.runs import RunManager

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
