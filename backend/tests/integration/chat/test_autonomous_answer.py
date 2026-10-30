"""真实运行图和数据库贯通，只有供应商模型使用可控替身。"""

import asyncio
import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from app.modules.chat.runs import RunManager
from tests.helpers.models import DeterministicModel

LINK = "[入口](source:Program.cs#L2-L2)"
LONG_TEXT = "Main 方法体为空，没有后续步骤。" * 140
ANSWERS = [
    "**" + LONG_TEXT + "**\n\n" + LINK,
    "| 方法 | 行为 |\n| --- | --- |\n| Main | 方法体为空 |\n\n" + LINK,
    "```rich-content\n"
    + json.dumps(
        {"version": 1, "blocks": [{"id": "body", "type": "text", "content": LONG_TEXT + LINK}]},
        ensure_ascii=False,
    )
    + "\n```",
]


@pytest.mark.parametrize("answer", ANSWERS, ids=["long-markdown", "table", "rich-text"])
async def test_search_read_review_display_and_history_preserve_model_format(
    services, monkeypatch, answer
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=32768, output_tokens=4096)))
    original_source = (workspace.root / "Program.cs").read_bytes()
    calls = {"main": 0, "review": 0}

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            if "独立的源码结论复核器" in messages[0].text:
                calls["review"] += 1
                result = AIMessage(content='{"verdict":"passed","issues":[]}')
            else:
                calls["main"] += 1
                assert "可选回答展示协议" in messages[0].text
                tools = {row.name for row in messages if isinstance(row, ToolMessage)}
                if "read_source" in tools:
                    result = AIMessage(content=answer)
                else:
                    name = "read_source" if "search_source" in tools else "search_source"
                    args = (
                        {"path": "Program.cs", "start_line": 2, "end_line": 2}
                        if name == "read_source"
                        else {"query": "Main", "glob": "*.cs"}
                    )
                    result = AIMessage(
                        content="", tool_calls=[{"id": name, "name": name, "args": args}]
                    )
            return ChatResult(generations=[ChatGeneration(message=result)])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    manager = RunManager(repository, runtime, settings)
    run = repository.create_run(
        None,
        "说明 Program.cs 的入口流程",
        [],
        {"use_knowledge": False, "use_memory": False, "use_deepwiki": False},
    )
    try:
        manager.start(run)
        await asyncio.wait_for(manager.tasks[run["id"]], timeout=20)
        saved = repository.run(run["id"])
        assert saved["status"] == "completed", saved.get("error")
        assert saved["answer"] == answer
        assert calls == {"main": 3, "review": 0}
        events = repository.events(run["id"])
        assert [row["payload"]["name"] for row in events if row["kind"] == "tool_start"] == [
            "search_source",
            "read_source",
        ]
        assert repository.run_event(run["id"], "answer_validation")["passed"]
        assert repository.run_event(run["id"], "answer_format_validation")["passed"]
        assert repository.run_event(run["id"], "source_review") is None
        assert not any(
            row["kind"] in {"answer_draft", "answer_presentation", "token"} for row in events
        )
        assert [row["payload"]["text"] for row in events if row["kind"] == "answer_replace"] == [
            answer
        ]
        assert repository.thread(run["thread_id"])["messages"][-1]["content"] == answer
        assert [row async for row in manager.stream(run["id"], after=0)] == events
        assert (workspace.root / "Program.cs").read_bytes() == original_source
    finally:
        await manager.shutdown()
        runtime.semantic.close()
