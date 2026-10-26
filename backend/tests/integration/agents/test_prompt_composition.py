"""在真实图装配边界核对规则、工具和来源开关，不调用供应商。"""

import pytest

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from app.modules.chat.schemas import SourceOptions
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.projects.context import bind_project


@pytest.mark.parametrize(
    ("project", "knowledge", "memory", "automatic"),
    [
        (False, False, False, False),
        (False, True, False, False),
        (True, False, False, False),
        (True, True, True, False),
        (True, True, True, True),
        (False, False, False, True),
    ],
)
async def test_prompt_rules_follow_available_tools_and_preserve_current_context(
    services, monkeypatch, project, knowledge, memory, automatic
):
    paths, database, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(
            model=ModelSettings(context_tokens=16384, output_tokens=512),
            mcp_servers=[],
            auto_memory=automatic,
        )
    )
    # 调试库为空时本来就不装配工具；预置可用记录才能检验开关，而非空库分支。
    DebugIssues(HandoverStore(database=database)).save(
        DebugWrite(title="测试调试经验", payload={"problem": "测试条件下的现象与处理记录"}), {}
    )
    repository.project_id = "prompt-project" if project else None
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    captured = {}
    graph = object()

    def create_graph(**kwargs):
        captured.update(kwargs)
        return graph

    # 仅替换外部图编译边界；规则选择、工具装配和上下文拼接实际执行。
    monkeypatch.setattr("app.agents.runtime.graph_builder.create_deep_agent", create_graph)
    verified = "\n<verified_source_context>本轮源码标记</verified_source_context>"
    with bind_project({"name": "本轮项目标记", "instructions": "本轮项目指令标记"}):
        result = await runtime.graph(
            "prompt-thread",
            None,
            lambda *_args: None,
            inspection=True,
            question_text="你好",
            source_options=SourceOptions(
                use_knowledge=knowledge, use_memory=memory, use_deepwiki=False
            ).model_dump(),
            verified_context=verified,
        )

    assert result is graph
    prompt = captured["system_prompt"]
    tools = {item.name for item in captured["tools"]}
    assert "本轮项目标记" in prompt and "本轮项目指令标记" in prompt
    assert verified in prompt
    assert "同路径异版本" in prompt
    assert "本轮未接入流程图谱、功能说明和交接资料" in prompt
    assert prompt.count("【回答方式】") == 1
    assert prompt.count("回答展示协议") == 1
    assert "[文件名:行号](source:相对路径#L行号)" in prompt

    assert ("项目工具要求：" in prompt) is project
    assert ("create_code_change" in tools) is project
    assert ("update_code_change_requirements" in prompt) is project
    assert ("调试经验检索：" in prompt) is knowledge
    assert ("search_debug_issues" in tools) is knowledge
    assert ("compatibility" in prompt) is knowledge
    assert ("remember" in tools) is memory
    assert ("本轮不检索或保存长期记忆" in prompt) is (not memory)
    assert ("可主动调用 remember" in prompt) is (memory and automatic)
    assert ("只有用户明确要求记住时才调用 remember" in prompt) is (memory and not automatic)
