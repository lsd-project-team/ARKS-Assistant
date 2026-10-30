from types import SimpleNamespace

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.agents.context.task_guidance import TaskGuidance
from app.agents.prompts.system import SYSTEM_PROMPT
from tests.helpers.models import DeterministicModel


async def effective_request(middleware, request=None):
    request = request or ModelRequest(
        model=DeterministicModel(),
        system_message=SystemMessage(content=SYSTEM_PROMPT),
        messages=[HumanMessage(content="当前问题")],
    )

    async def handler(current):
        return current

    return await middleware.awrap_model_call(request, handler)


@pytest.mark.parametrize("question", ["你好", "介绍 Vue", "蓝膜刺穿处理经验", "周末活动流程"])
async def test_general_questions_keep_source_and_device_display_rules_out(question):
    current = await effective_request(TaskGuidance(question, {"read_source"}))
    assert "【源码核查】" not in current.system_message.text
    assert "回答展示协议" not in current.system_message.text
    assert (
        "当前软件实现、代码流程或参数计算必须读取当前源码"
        in current.system_message.text
    )
    assert "问题与经验已覆盖的工艺处理建议可按该经验回答" in current.system_message.text


@pytest.mark.parametrize("question", ["Program.cs 的入口是什么", "设备标定流程"])
async def test_source_rules_do_not_force_a_flow_layout(question):
    current = await effective_request(TaskGuidance(question, {"read_source"}))
    prompt = current.system_message.text
    assert prompt.count("【源码核查】") == 1
    assert "[文件名:行号](source:相对路径#L行号)" in prompt
    assert "本地源码优先于 DeepWiki" in prompt
    assert "发起调用不等于硬件完成" in prompt
    assert "默认用step_flow" not in prompt
    assert "先规划候选项并调用 plan_source_checks" not in prompt


@pytest.mark.parametrize("required,reads", [(True, []), (False, [{"path": "Program.cs"}])])
async def test_selections_and_restored_reads_keep_rules_for_short_followups(required, reads):
    middleware = TaskGuidance(
        "继续", {"read_source"}, SimpleNamespace(required=required, reads=reads)
    )
    current = await effective_request(middleware)
    assert "【源码核查】" in current.system_message.text


@pytest.mark.parametrize(
    ("name", "args", "source"),
    [
        ("find_source_files", {"pattern": "*.cs"}, True),
        ("csharp_relations", {"path": "Program.cs"}, True),
        ("read_file", {"file_path": "/workspace/Program.cs"}, True),
        ("grep", {"path": "/workspace", "pattern": "Main"}, True),
        ("read_file", {"file_path": "/threads/example/result.txt"}, False),
        ("search_debug_issues", {"query": "蓝膜"}, False),
    ],
)
async def test_actual_source_tool_choice_activates_rules_without_affecting_other_tools(
    name, args, source
):
    middleware = TaskGuidance("能否进一步解释", {"find_source_files", "csharp_relations"})
    before = await effective_request(middleware)
    assert "【源码核查】" not in before.system_message.text
    tool = SimpleNamespace(tool_call={"id": "call-1", "name": name, "args": args})

    async def handler(request):
        return ToolMessage(content="实际工具结果", tool_call_id=request.tool_call["id"])

    result = await middleware.awrap_tool_call(tool, handler)
    assert result.content == "实际工具结果"
    after = await effective_request(middleware)
    assert ("【源码核查】" in after.system_message.text) is source
    assert "【源码核查】" not in before.system_message.text
    fresh = await effective_request(TaskGuidance("你好", {"find_source_files"}))
    assert "【源码核查】" not in fresh.system_message.text


async def test_deep_task_keeps_report_rules_and_preserves_request_metadata_and_messages():
    system = SystemMessage(
        content=[{"type": "text", "text": "已有系统上下文"}],
        additional_kwargs={"test_metadata": "keep"},
    )
    messages = [HumanMessage(content="完整核查当前项目")]
    request = ModelRequest(model=DeterministicModel(), system_message=system, messages=messages)
    current = await effective_request(TaskGuidance("继续", {"read_source"}, deep=True), request)
    assert "先规划候选项并调用 plan_source_checks" in current.system_message.text
    assert current.system_message.text.startswith("已有系统上下文")
    assert current.system_message.additional_kwargs == {"test_metadata": "keep"}
    assert current.messages == messages
    assert system.text == "已有系统上下文"
    assert request.system_message is system
