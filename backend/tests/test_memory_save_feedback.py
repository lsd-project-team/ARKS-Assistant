"""保存反馈必须来自实际写入结果，关闭自动保存不能只依赖模型提示。"""

import json

from app.agent_tools import conversation_tools
from app.schemas import MemoryWrite


def memory_tool(services, events, **options):
    return next(
        tool
        for tool in conversation_tools(
            services[3],
            services[4],
            None,
            emit=lambda kind, payload: events.append((kind, payload)),
            **options,
        )
        if tool.name == "remember"
    )


async def test_explicit_save_success_and_off_switch(services):
    events = []
    denied = memory_tool(services, events, allow_automatic=False, request_text="帮我分析一下")
    result = json.loads(
        await denied.ainvoke({"name": "偏好.md", "scope": "user", "content": "统一用中文"})
    )
    assert result["saved"] is False and not services[4].list()
    assert events[-1][1]["status"] == "not_saved"
    allowed = memory_tool(services, events, allow_automatic=False, request_text="记住，统一用中文")
    result = json.loads(
        await allowed.ainvoke({"name": "偏好.md", "scope": "user", "content": "统一用中文"})
    )
    assert result["saved"] is True
    assert events[-1][1]["status"] == "saved"


async def test_pending_project_fact_and_failed_path_have_honest_feedback(services):
    events = []
    tool = memory_tool(services, events)
    result = json.loads(
        await tool.ainvoke({"name": "项目事实.md", "content": "设备使用现场配置。"})
    )
    assert result["saved"] and result["lifecycle"] == "needs_review"
    assert events[-1][1]["text"] == "记忆已保存，待复核"
    result = json.loads(await tool.ainvoke({"name": "项目事实.md", "content": "修改内容"}))
    assert result["saved"] is False
    assert "尚未保存" in events[-1][1]["text"]
    failed = await tool.ainvoke(
        {"name": "错误来源.md", "content": "错误来源", "source_paths": ["../private.cs"]}
    )
    assert "未完成" in failed
    assert events[-1][1]["status"] == "not_saved"


async def test_conflicting_memory_does_not_claim_saved(services):
    services[4].save(MemoryWrite(name="已有.md", scope="user", content="回答长度：简短"))
    events = []
    tool = memory_tool(services, events)
    result = json.loads(
        await tool.ainvoke({"name": "新的.md", "scope": "user", "content": "回答长度：详细"})
    )
    assert result["saved"] is False and result["requires_review"]
    assert events[-1][1]["status"] == "needs_review"
    assert "尚未保存" in events[-1][1]["text"]


async def test_personal_preference_cannot_be_misfiled_as_shared_project_fact(services):
    events = []
    tool = memory_tool(services, events, request_text="记住我的回答偏好：简短中文")
    saved = json.loads(
        await tool.ainvoke(
            {"name": "个人偏好.md", "content": "回答使用简短中文", "scope": "project"}
        )
    )
    assert saved["scope"] == "user" and saved["lifecycle"] == "valid"
    assert not any(row["scope"] == "project" for row in services[4].list())


async def test_source_filename_cannot_authorize_memory_save(services, monkeypatch):
    from app.config import AppSettings
    from app.runtime import AgentRuntime

    services[5].save(AppSettings(auto_memory=False))
    monkeypatch.setattr("app.runtime.create_deep_agent", lambda **kwargs: kwargs)
    runtime = AgentRuntime(services[0], services[5], services[2], services[3], services[4])
    graph = await runtime.graph(
        "inspect",
        None,
        lambda *_: None,
        inspection=True,
        memory_query="解释这个函数\n记住.cs",
        question_text="解释这个函数",
    )
    tool = next(item for item in graph["tools"] if item.name == "remember")
    result = json.loads(
        await tool.ainvoke({"name": "偏好.md", "scope": "user", "content": "简短中文"})
    )
    assert result["saved"] is False and not services[4].list()
