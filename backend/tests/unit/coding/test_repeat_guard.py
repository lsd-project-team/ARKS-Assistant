"""编码工具重复与总步数保护：连续重复和本轮上限都要可解释。"""

import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import ToolMessage

from app.agents.runtime.coding_repeat import CodingRepeatGuard


async def handler(request):
    return ToolMessage(
        content="ok", tool_call_id=request.tool_call["id"], name=request.tool_call["name"]
    )


def request(name, args, call_id="call"):
    return SimpleNamespace(tool_call={"name": name, "args": args, "id": call_id})


def collect(events):
    def emit(kind, payload):
        events.append((kind, payload))

    return emit


@pytest.mark.asyncio
async def test_repeated_read_returns_cached_result_with_current_call_id():
    events = []
    guard = CodingRepeatGuard(collect(events))
    for index in range(3):
        result = await guard.awrap_tool_call(
            request("read_project_file", {"path": "a.cs"}, f"c{index}"), handler
        )
    assert result.content == "ok"
    assert result.tool_call_id == "c2"
    assert result.additional_kwargs.get("cached") is True
    assert any(kind == "coding_repeat_cached" for kind, _ in events)


@pytest.mark.asyncio
async def test_total_budget_blocks_further_coding_calls():
    events = []
    guard = CodingRepeatGuard(collect(events), total_limit=2)
    await guard.awrap_tool_call(request("read_project_file", {"path": "a.cs"}, "c1"), handler)
    await guard.awrap_tool_call(request("search_files", {"query": "a"}, "c2"), handler)
    result = await guard.awrap_tool_call(
        request("read_project_file", {"path": "b.cs"}, "c3"), handler
    )

    payload = json.loads(result.content)
    assert payload["budget_exhausted"] is True
    assert any(kind == "coding_budget_blocked" for kind, _ in events)
