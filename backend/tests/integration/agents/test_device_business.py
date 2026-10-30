"""设备业务问法须核对源码，主工程优先规则进入实际模型上下文。"""

import pytest
from langchain_core.messages import SystemMessage

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from tests.helpers.models import DeterministicModel


@pytest.mark.parametrize(
    ("question", "required"),
    [
        ("我想做设备标定，给我输出一下标定流程", True),
        ("吸嘴怎么校准", True),
        ("固晶时取片失败怎么办", True),
        ("点胶和晶圆搬运的先后顺序是什么", True),
        ("设备回零的前置条件有哪些", True),
        ("如何进行设备标定", True),
        ("设备标定\n请列出步骤", True),
        ("请解释 Program.cs 的入口", True),
        ("取片不稳定有哪些处理经验", False),
        ("查一下历史标定记录", False),
        ("帮我规划一下周末活动的流程", False),
        ("你好", False),
        ("帮我润色一下这段文字", False),
    ],
)
async def test_business_question_requires_source_without_selection(
    services, monkeypatch, question, required
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=16384, output_tokens=512)))
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)

    class ReachedGraph(Exception):
        pass

    async def graph(*_args, **kwargs):
        evidence = kwargs["evidence"]
        assert evidence.required is required
        # 未读源码的业务回答必须失败，不能把搜索线索当成已经核实的依据。
        report = evidence.check("请按操作界面完成设备标定。")
        assert report["passed"] is not required
        if required:
            assert "本轮缺少已核对的本地源码" in report["reasons"]
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
            return super()._generate(messages, *args, **kwargs)

    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_args, **_kwargs: Model()
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    options = {"use_knowledge": False, "use_memory": False, "use_deepwiki": False}
    run = repository.create_run(None, "我想做设备标定，给我输出一下标定流程", [], options)
    answer = await runtime.execute(run, lambda *_args: None)
    prompt = "\n".join(system_prompts)
    assert "优先在 AKRS.ZX2200/ 中检索" in prompt
    assert "再根据已读取的调用关系" in prompt
    assert "用户明确指定的文件或附带选区应先核对" in prompt
    assert "其他项目不能套用这个目录" in prompt
    assert "源码核对提示" in answer
