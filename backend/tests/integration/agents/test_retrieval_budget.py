from types import SimpleNamespace

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import ToolMessage
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
