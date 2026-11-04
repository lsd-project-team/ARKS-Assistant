"""自动修复中间件只重试当前轮次的实际失败，保留取消和次数边界。"""

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.agents.runtime.code_work_repair import CodeWorkRepair


@pytest.mark.parametrize(
    "status,attempt,run_id,expected_calls",
    [
        ("failed", 1, "current", 2),
        ("failed", 3, "current", 1),
        ("cancelled", 1, "current", 1),
        ("passed", 1, "current", 1),
        ("failed", 1, "other", 1),
    ],
)
async def test_repair_reenters_tools_only_for_eligible_failure(
    status, attempt, run_id, expected_calls
):
    job = {
        "id": "job",
        "run_id": run_id,
        "status": status,
        "attempt": attempt,
        "error": "compile failed",
        "steps": [{"name": "compile", "status": "failed", "log": "Example.cs(3): error CS1002"}],
    }
    work = SimpleNamespace(status=lambda thread: {"revision": 2, "verification": job})
    events, requests = [], []
    middleware = CodeWorkRepair(work, "thread", "current", lambda *args: events.append(args))
    request = SimpleNamespace(messages=[], override=lambda **kwargs: SimpleNamespace(**kwargs))

    async def handler(value):
        requests.append(value)
        if len(requests) == 2:
            return SimpleNamespace(
                result=[
                    AIMessage(
                        content="",
                        tool_calls=[
                            {"id": "read", "name": "read_work_file", "args": {"path": "Example.cs"}}
                        ],
                    )
                ]
            )
        return SimpleNamespace(result=[AIMessage(content="done")])

    response = await middleware.awrap_model_call(request, handler)
    assert len(requests) == expected_calls
    if expected_calls == 2:
        assert response.result[0].tool_calls[0]["name"] == "read_work_file"
        assert "CS1002" in requests[1].messages[-1].content
        assert "保留已固定的验收断言" in requests[1].messages[-1].content
    else:
        assert not response.result[0].tool_calls
