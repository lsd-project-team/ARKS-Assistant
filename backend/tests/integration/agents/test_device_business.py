"""普通问题先选择来源，实际查询源码后注入主工程及证据规则。"""

import pytest
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from tests.helpers.models import DeterministicModel


@pytest.mark.parametrize(
    "question",
    [
        "我想做设备标定，给我输出一下标定流程",
        "吸嘴怎么校准",
        "固晶时取片失败怎么办",
        "点胶和晶圆搬运的先后顺序是什么",
        "设备回零的前置条件有哪些",
        "如何进行设备标定",
        "设备标定\n请列出步骤",
        "请解释 Program.cs 的入口",
        "取片不稳定有哪些处理经验",
        "查一下历史标定记录",
        "帮我规划一下周末活动的流程",
        "你好",
        "帮我润色一下这段文字",
    ],
)
async def test_question_keywords_do_not_force_source_before_routing(
    services, monkeypatch, question
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=16384, output_tokens=512)))
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)

    class ReachedGraph(Exception):
        pass

    async def graph(*_args, **kwargs):
        evidence = kwargs["evidence"]
        assert not evidence.required and not evidence.mandatory
        raise ReachedGraph

    monkeypatch.setattr(runtime, "graph", graph)
    run = repository.create_run(None, question, [])
    with pytest.raises(ReachedGraph):
        await runtime.execute(run, lambda *_args: None)


async def test_main_project_priority_reaches_model_with_optional_sources_disabled(
    services, monkeypatch
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(model=ModelSettings(context_tokens=16384, output_tokens=512), mcp_servers=[])
    )
    system_prompts = []

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            system_prompts.extend(
                message.text for message in messages if isinstance(message, SystemMessage)
            )
            if any(isinstance(row, ToolMessage) for row in messages):
                answer = AIMessage(content="入口为空。[Program.cs:2](source:Program.cs#L2)")
            else:
                answer = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "read",
                            "name": "read_source",
                            "args": {"path": "Program.cs", "start_line": 2, "end_line": 2},
                        }
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=answer)])

    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_args, **_kwargs: Model()
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    options = {"use_knowledge": False, "use_memory": False, "use_deepwiki": False}
    run = repository.create_run(None, "我想做设备标定，给我输出一下标定流程", [], options)
    events = []
    answer = await runtime.execute(run, lambda kind, payload: events.append((kind, payload)))
    prompt = "\n".join(system_prompts)
    assert "优先在 AKRS.ZX2200/ 中检索" in prompt
    assert "再根据已读取的调用关系" in prompt
    assert "用户明确指定的文件或附带选区应先核对" in prompt
    assert "其他项目不能套用这个目录" in prompt
    assert "源码核对提示" not in answer
    validation = [payload for kind, payload in events if kind == "answer_validation"][-1]
    assert validation["passed"]
