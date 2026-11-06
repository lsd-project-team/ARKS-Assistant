import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import SystemMessage, ToolMessage

from app.agents.runtime.code_work_reads import CodeWorkReadProgress
from app.agents.tools.code_work import code_work_tools
from tests.helpers.code_work import FILE, make_work


@pytest.fixture
def guarded(services, tmp_path):
    work, thread, _ = make_work(services, tmp_path)
    middleware = CodeWorkReadProgress(lambda *args: None)
    tools = {tool.name: tool for tool in code_work_tools(work, thread, lambda *args: None)}

    async def call(name="read_work_file", **arguments):
        request = SimpleNamespace(tool_call={"id": "call", "name": name, "args": arguments})

        async def handler(value):
            result = await tools[name].ainvoke(value.tool_call["args"])
            return ToolMessage(content=result, tool_call_id="call", name=name)

        return await middleware.awrap_tool_call(request, handler)

    return middleware, work, thread, call


async def model_tools(middleware):
    class Request:
        tools = [
            {"name": name} for name in ["read_work_file", "edit_work_file", "verify_code_workspace"]
        ]
        system_message = SystemMessage(content="原系统提示")

        def override(self, **values):
            return SimpleNamespace(**values)

    async def model(value):
        return [item["name"] for item in value.tools], value.system_message.text

    return await middleware.awrap_model_call(Request(), model)


async def test_repeated_real_read_preserves_version_and_only_pauses_one_model_decision(guarded):
    middleware, _, _, call = guarded
    first = json.loads((await call(path=FILE)).text)
    assert "1: class Example" in first["content"]
    await call(path=FILE)
    repeated = await call(path=FILE)
    compact = json.loads(repeated.text)
    assert repeated.additional_kwargs["cached"] is True
    assert compact["version"] == first["version"]
    assert compact["path"] == FILE and compact["start_line"] == 1 and compact["end_line"] == 300
    assert "content" not in compact
    names, prompt = await model_tools(middleware)
    assert names == ["edit_work_file", "verify_code_workspace"]
    assert first["version"] in prompt and "原系统提示" in prompt
    names, _ = await model_tools(middleware)
    assert "read_work_file" in names


async def test_new_range_and_changed_file_version_remain_readable(guarded):
    middleware, work, thread, call = guarded
    for _ in range(3):
        await call(path=FILE, start_line=1, end_line=3)
    other = json.loads((await call(path=FILE, start_line=2, end_line=4)).text)
    assert "2:  // 中文" in other["content"]
    assert "read_work_file" in (await model_tools(middleware))[0]
    for _ in range(3):
        await call(path=FILE, start_line=2, end_line=4)
    version = work.read(thread, FILE)["version"]
    work.write(thread, FILE, "class Example { int Value = 42; }", version)
    changed = json.loads((await call(path=FILE, start_line=2, end_line=4)).text)
    assert changed["version"] != version and "content" in changed
    assert "read_work_file" in (await model_tools(middleware))[0]


async def test_edit_after_repeated_read_still_executes_and_resets_read_pause(guarded):
    middleware, work, thread, call = guarded
    version = work.read(thread, FILE)["version"]
    for _ in range(3):
        await call(path=FILE)
    await call(
        "edit_work_file",
        path=FILE,
        old_text="int Value = 1;",
        new_text="int Value = 8;",
        version=version,
    )
    assert "int Value = 8;" in work.read(thread, FILE)["content"]
    assert "read_work_file" in (await model_tools(middleware))[0]


async def test_failed_tool_result_never_resets_progress(guarded):
    middleware, _, _, call = guarded
    for _ in range(3):
        await call(path=FILE)
    request = SimpleNamespace(tool_call={"name": "edit_work_file"})

    async def failure(value):
        return ToolMessage(content="文件版本冲突", status="error", tool_call_id="failed")

    await middleware.awrap_tool_call(request, failure)
    assert "read_work_file" not in (await model_tools(middleware))[0]
