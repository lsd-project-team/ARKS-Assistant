"""运行级计划与验收检查：状态流转与缺失项判定。"""

import pytest

from app.agents.runtime.checks import RunChecks
from app.agents.runtime.plan import PlanStore


def test_technical_complete_ignores_plan():
    checks = RunChecks(generation=True)
    checks.record_verify({"ok": True, "kind": "build"})
    checks.record_verify({"ok": True, "kind": "test"})
    checks.record_ui({"ok": True})
    assert checks.technical_complete() is True
    assert checks.missing(False, include_plan=False) == []
    checks.record_verify({"ok": True, "kind": "build", "warning_count": 2})
    assert checks.technical_complete() is False


async def test_gate_forces_answer_when_technical_checks_pass():
    from langchain.agents.middleware.types import ModelRequest
    from langchain_core.messages import AIMessage, HumanMessage

    from app.agents.runtime.checks import AcceptanceGate, RunChecks
    from app.agents.runtime.plan import PlanStore
    from app.infrastructure.providers.models import StateInspectionModel

    checks, plan, events = RunChecks(generation=True), PlanStore(), []
    checks.record_verify({"ok": True, "kind": "build"})
    checks.record_verify({"ok": True, "kind": "test"})
    checks.record_ui({"ok": True})
    plan.update([{"title": "还在打磨", "status": "doing"}])
    choices = []

    async def handler(request):
        choices.append(request.tool_choice)
        return type("Response", (), {"result": [AIMessage(content="技术验收已通过，收尾。")]})()

    gate = AcceptanceGate(checks, plan, lambda *args: events.append(args), generation=True)
    request = ModelRequest(model=StateInspectionModel(), messages=[HumanMessage(content="做")])
    await gate.awrap_model_call(request, handler)
    assert choices and choices[0] in ("none", {"type": "none"})
    assert events[-1][1]["ok"] is True and events[-1][1]["plan_incomplete"] is True


async def test_gate_recovers_ui_before_finishing():
    from langchain.agents.middleware.types import ModelRequest
    from langchain_core.messages import AIMessage, HumanMessage

    from app.agents.runtime.checks import AcceptanceGate, RunChecks
    from app.agents.runtime.plan import PlanStore
    from app.infrastructure.providers.models import StateInspectionModel

    checks, plan, events = RunChecks(generation=True), PlanStore(), []
    checks.record_verify({"ok": True, "kind": "build"})
    checks.record_ui({"ok": False, "issues": ["标签页高度过小"]})
    plan.update([{"title": "验收", "status": "done"}])
    recovered = []

    def recover():
        recovered.append(True)
        return {"ok": True, "shots": ["shots/ui_tab0.png"], "recovered_from": "abc"}

    async def handler(request):
        return type("Response", (), {"result": [AIMessage(content="已回退到通过状态并收尾")]})()

    gate = AcceptanceGate(
        checks, plan, lambda *args: events.append(args), generation=True, recover=recover
    )
    request = ModelRequest(model=StateInspectionModel(), messages=[HumanMessage(content="做")])
    await gate.awrap_model_call(request, handler)
    assert recovered == [True]
    assert checks.ui and checks.ui.get("ok") is True
    assert any(event[1].get("recovered") for event in events)
    assert events[-1][1]["ok"] is True


def test_generation_intent_detection():
    from app.agents.analysis.policy import is_generation_request, wants_winforms

    assert is_generation_request("从零实现完整的 SP900 点胶机上位机") is True
    assert is_generation_request("生成界面骨架并自检") is True
    assert is_generation_request("帮我编写一个 WinForms 程序") is True
    assert is_generation_request("这个项目页面布局有问题，你看下") is False
    assert is_generation_request("怎么实现快速排序？") is False
    assert wants_winforms("实现 SP900 点胶机上位机") is True
    assert wants_winforms("用 C# 写一个窗体") is True
    assert wants_winforms("做一个 3D 网页游戏") is False


def test_plan_store_normalizes_and_requires_completion():
    store = PlanStore()
    items = store.update(
        [
            {"title": "协议层", "status": "doing", "note": "先写回放"},
            {"title": "界面", "status": "todo"},
        ]
    )
    assert [item["status"] for item in items] == ["doing", "todo"]
    assert store.complete() is False
    store.update(
        [
            {"title": "协议层", "status": "done"},
            {"title": "界面", "status": "blocked", "note": "缺设备"},
        ]
    )
    assert store.complete() is True
    assert "受阻" in store.text() and "缺设备" in store.text()


def test_plan_store_rejects_bad_input():
    store = PlanStore()
    with pytest.raises(ValueError):
        store.update([])
    with pytest.raises(ValueError):
        store.update([{"title": "", "status": "todo"}])
    with pytest.raises(ValueError):
        store.update([{"title": "a", "status": "unknown"}])


async def test_update_plan_tool_emits_event():
    from app.agents.tools.plan import plan_tools

    store, events = PlanStore(), []
    tool = plan_tools(store, lambda *args: events.append(args))[0]
    result = await tool.ainvoke({"items": [{"title": "构建", "status": "done"}]})
    assert '"ok":true' in result.replace(" ", "")
    assert events[-1][0] == "plan" and events[-1][1]["ok"] is True
    assert store.complete() is True


def test_checks_require_plan_verify_and_ui():
    checks = RunChecks(generation=True)
    assert len(checks.missing(plan_complete=False)) == 3
    checks.record_verify({"ok": True, "kind": "build"})
    checks.record_ui({"ok": False})
    missing = checks.missing(plan_complete=True)
    assert len(missing) == 1 and "check_ui" in missing[0]
    checks.record_ui({"ok": True})
    assert checks.missing(plan_complete=True) == []
    # 非生成任务不强制自测。
    assert RunChecks(generation=False).missing(True) == [
        "未通过 verify build（构建 0 错误，最好 0 警告）",
        "未通过 check_ui（界面截图与布局自检）",
    ]
    # 实际跑过且失败的自测仍然拦截。
    checks.record_verify({"ok": False, "kind": "test", "failed": 1})
    assert any("verify test 未通过" in item for item in checks.missing(True))


async def test_acceptance_gate_asks_for_missing_work_then_passes():
    from langchain.agents.middleware.types import ModelRequest
    from langchain_core.messages import AIMessage, HumanMessage

    from app.agents.runtime.checks import AcceptanceGate
    from app.infrastructure.providers.models import StateInspectionModel

    checks, plan, events = RunChecks(generation=True), PlanStore(), []
    plan.update([{"title": "界面自检", "status": "doing"}])
    calls = []

    async def handler(request):
        calls.append(request.messages)
        return type("Response", (), {"result": [AIMessage(content="完成")]})()

    gate = AcceptanceGate(checks, plan, lambda *args: events.append(args), generation=True)
    request = ModelRequest(model=StateInspectionModel(), messages=[HumanMessage(content="做")])
    await gate.awrap_model_call(request, handler)
    # 第一次缺计划/构建/自测/界面，被要求继续一次。
    assert len(calls) == 2
    assert events[-1][0] == "acceptance" and events[-1][1]["ok"] is False
    assert events[-1][1]["missing"]
    # 补齐后再次调用直接放行。
    checks.record_scaffold({"ok": True})
    checks.record_verify({"ok": True, "kind": "build"})
    checks.record_verify({"ok": True, "kind": "test"})
    checks.record_ui({"ok": True})
    plan.update([{"title": "界面自检", "status": "done"}])
    gate = AcceptanceGate(checks, plan, lambda *args: events.append(args), generation=True)
    await gate.awrap_model_call(request, handler)
    assert events[-1][1]["ok"] is True

