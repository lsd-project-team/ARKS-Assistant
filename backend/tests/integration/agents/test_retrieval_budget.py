from types import SimpleNamespace

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.agents.analysis.retrieval_budget import RetrievalBudget
from tests.helpers.models import DeterministicModel


async def test_budget_limits_tool_execution_and_requires_source_based_final_answer():
    events, called, requests = [], [], []
    middleware = RetrievalBudget(lambda *event: events.append(event), max_calls=2)

    async def tool_handler(request):
        called.append(request.tool_call["id"])
        return ToolMessage(content="源码证据", tool_call_id=request.tool_call["id"])

    results = []
    for index in range(4):
        results.append(
            await middleware.awrap_tool_call(
                SimpleNamespace(tool_call={"id": str(index), "name": "read_source"}), tool_handler
            )
        )
    assert called == ["0", "1"] and results[-1].status == "error"
    assert len(events) == 1
    request = ModelRequest(
        model=DeterministicModel(), messages=[], tools=[], state={"messages": []}, runtime=None
    )

    async def model_handler(current):
        requests.append(current)
        return "final"

    assert await middleware.awrap_model_call(request, model_handler) == "final"
    assert requests[0].tool_choice == "none" and "未核查" in requests[0].system_message.text
    assert not requests[0].messages
    assert results[-1].additional_kwargs["execution_status"] == "skipped"


@pytest.mark.parametrize("protocol", ["anthropic", "openai"])
async def test_budget_uses_protocol_specific_stop_choice(protocol):
    model = (
        ChatAnthropic(model="test", api_key="test")
        if protocol == "anthropic"
        else ChatOpenAI(model="test", api_key="test")
    )
    middleware = RetrievalBudget(lambda *_: None, max_calls=0)
    request = ModelRequest(model=model, messages=[], tools=[], state={"messages": []}, runtime=None)

    async def handler(current):
        return current.tool_choice

    assert await middleware.awrap_model_call(request, handler) == (
        {"type": "none"} if protocol == "anthropic" else "none"
    )


@pytest.mark.parametrize("used", [1, 2])
async def test_retrieval_reserve_and_exhaustion_keep_document_workflow_available(used):
    budget = RetrievalBudget(lambda *_: None, max_calls=2, reserve=1)
    budget.workflow_tools = frozenset({"read_chat_attachment", "search_chat_attachment"})
    executed = []

    async def handler(request):
        executed.append(request.tool_call["name"])
        return ToolMessage(content="actual boundary executed", tool_call_id=request.tool_call["id"])

    for index in range(used):
        await budget.awrap_tool_call(
            SimpleNamespace(tool_call={"id": str(index), "name": "read_source"}), handler
        )
    for name in ("read_chat_attachment", "search_chat_attachment"):
        result = await budget.awrap_tool_call(
            SimpleNamespace(tool_call={"id": name, "name": name}), handler
        )
        assert result.status == "success", result.content
    assert executed[-2:] == ["read_chat_attachment", "search_chat_attachment"]
    assert budget.used == used
    assert budget.counts["attempted"] == used

    @tool
    def read_chat_attachment(attachment_id: str) -> str:
        """Read a bound attachment."""
        return attachment_id

    tools = [read_chat_attachment, {"type": "function", "function": {"name": "read_source"}}]
    request = ModelRequest(
        model=DeterministicModel(), messages=[], tools=tools, state={"messages": []}, runtime=None
    )

    async def model_handler(current):
        assert current.tool_choice != "none"
        assert read_chat_attachment in current.tools
        assert "附件" in current.system_message.text
        if used == 2:
            assert current.tools == [read_chat_attachment]
        return "workflow can continue"

    assert await budget.awrap_model_call(request, model_handler) == "workflow can continue"


@pytest.mark.parametrize("with_workflow", [False, True])
async def test_repeated_cached_reads_cannot_loop_until_graph_recursion_limit(with_workflow):
    evidence = SimpleNamespace(cached=lambda *_: True)
    budget = RetrievalBudget(lambda *_: None, max_calls=24, evidence=evidence)
    if with_workflow:
        budget.workflow_tools = frozenset({"search_chat_attachment"})
    called = []

    async def tool_handler(request):
        called.append(request.tool_call["id"])
        return ToolMessage(content="same version and range", tool_call_id=request.tool_call["id"])

    for index in range(6):
        await budget.awrap_tool_call(
            SimpleNamespace(tool_call={"id": str(index), "name": "read_source_batch", "args": {}}),
            tool_handler,
        )
    assert len(called) == 3
    assert budget.counts["cached"] == 3 and budget.counts["skipped"] == 3
    request = ModelRequest(
        model=DeterministicModel(),
        messages=[],
        tools=[{"name": "search_chat_attachment"}],
        state={"messages": []},
        runtime=None,
    )

    async def model_handler(current):
        assert "重复" in current.system_message.text
        if with_workflow:
            assert (
                current.tools == [{"name": "search_chat_attachment"}]
                and current.tool_choice != "none"
            )
        else:
            assert current.tool_choice == "none"
        return "stopped rereading"

    assert await budget.awrap_model_call(request, model_handler) == "stopped rereading"


async def test_distinct_cached_ranges_remain_free_and_changing_reason_does_not_hide_repeat():
    budget = RetrievalBudget(lambda *_: None, evidence=SimpleNamespace(cached=lambda *_: True))
    executed = []

    async def handler(request):
        executed.append(request.tool_call["id"])
        return ToolMessage(content="cached source", tool_call_id=request.tool_call["id"])

    async def call(line, reason):
        return await budget.awrap_tool_call(
            SimpleNamespace(
                tool_call={
                    "id": f"{line}:{reason}",
                    "name": "read_source_batch",
                    "args": {
                        "ranges": [
                            {
                                "path": "Example.cs",
                                "start_line": line,
                                "end_line": line + 1,
                                "reason": reason,
                            }
                        ]
                    },
                }
            ),
            handler,
        )

    for line in (1, 3, 5, 7):
        assert (await call(line, "read context")).status == "success"
    assert not budget.stalled and budget.used == 0
    await call(1, "repeat differently")
    await call(1, "another explanation")
    rejected = await call(1, "one more explanation")
    assert rejected.status == "error" and len(executed) == 6
    assert rejected.additional_kwargs["skip_reason"] == "repeated_read"
