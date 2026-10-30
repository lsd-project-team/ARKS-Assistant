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
    # 有记录也只装配可选工具，问候不应因此触发自动检索或注入记录。
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
    with bind_project(
        {"name": "本轮项目标记", "instructions": "旧项目指令标记", "description": "旧项目说明标记"}
    ):
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
    assert "本轮项目标记" in prompt
    assert "旧项目指令标记" not in prompt and "旧项目说明标记" not in prompt
    assert verified in prompt
    assert "同路径异版本" in prompt
    assert "本轮未接入流程图谱、功能说明和交接资料" in prompt
    assert prompt.count("【回答方式】") == 1
    assert "可选回答展示协议" in prompt
    assert "默认用step_flow" not in prompt
    assert "【源码核查】" not in prompt
    assert "当前软件实现、代码流程或参数计算必须读取当前源码" in prompt
    assert "问题与经验已覆盖的工艺处理建议可按该经验回答" in prompt
    assert "不把经验问答自动扩成源码排查" in prompt
    assert "用户要求图文并茂或示意图时" in prompt
    assert "不能声称是原图、实物照片或已执行的验证" in prompt

    assert "项目工具要求：" not in prompt
    assert "create_code_change" not in tools
    assert "edit_change_file" not in tools and "verify_code_change" not in tools
    assert "update_code_change_requirements" not in prompt
    assert "没有修改文件、执行命令或审核交付工具" in prompt
    assert ("问题识别与查询路由" in prompt) is knowledge
    assert ("search_debug_issues" in tools) is knowledge
    assert ("与项目相关：" in prompt) is knowledge
    assert ("与项目无关：" in prompt) is knowledge
    assert "remember" not in tools
    assert ("本轮不使用长期记忆" in prompt) is (not memory)
    assert "长期记忆由后台" in prompt
    assert "没有即时保存或修改记忆工具" in prompt
