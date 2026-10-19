"""真实临时副本验证命令授权、需求传递和只讨论约束。"""

import asyncio
import json

import pytest

from app.agents.analysis.policy import analysis_policy
from app.agents.tools.engineering import engineering_tools


@pytest.fixture
def runtime(services):
    from app.bootstrap import create_services

    current = create_services(services[0])
    current.repository.project_id = "edit-intent"
    yield current.runtime
    current.runtime.semantic.close()
    current.database.close()


def tools(runtime, request):
    return {tool.name: tool for tool in engineering_tools(runtime, request)}


@pytest.mark.parametrize(
    "prompt",
    [
        "新增一个边界检查",
        "请添加一个方法",
        "删除旧函数",
        "把旧函数移除",
        "重命名入口",
        "请重构这个模块",
        "将按钮改成新名称",
        "请在隔离副本修改入口，不要修改原件",
        "请在隔离副本修改Program.cs，把值从1改为2。原件不变；约束仅修改Program.cs；查看差异。",
        "请在隔离副本修改Program.cs，保持原文件不变，修改范围仅限Program.cs。",
        "请在隔离副本修复入口，不修改测试、点值替身、工程文件或原件。",
        "请修改入口，不要修改测试或配置。",
        "请修复入口；禁止修改Tests.cs。",
        "请修改入口，不修改原件和原始文件。请在隔离副本处理。",
        "请在隔离副本修复入口，不修改测试、配置或调用片段。",
        "好的开始吧\n此前已授权的请求：请修复返回值，先给我方案",
    ],
)
async def test_explicit_actions_create_real_copy_with_user_contract(runtime, prompt):
    original = (runtime.workspace.root / "Program.cs").read_bytes()
    result = json.loads(
        await tools(runtime, prompt)["create_code_change"].ainvoke(
            {
                "title": "修改入口",
                "goal": "保留原件",
                "acceptance_criteria": ["入口仍可读取"],
                "constraints": "不得引入外部依赖",
                "allowed_paths": ["Program.cs"],
            }
        )
    )
    assert result["id"] and result["constraints"] == "不得引入外部依赖"
    assert result["acceptance_criteria"] == ["入口仍可读取"]
    assert (runtime.workspace.root / "Program.cs").read_bytes() == original


@pytest.mark.parametrize(
    "prompt",
    [
        "如何新增一个方法",
        "新增功能需要多少时间？",
        "修改代码需要哪些步骤",
        "修改代码，需要哪些步骤",
        "实现原理为何这样",
        "新增模块要多久",
        "请解释如何删除旧函数",
        "新增这个合理吗",
        "请修复返回值，先回答我",
        "请添加一个方法，不要修改代码",
        "请修复返回值，不要写代码",
        "请修复返回值，但不修改代码",
        "请新增校验，禁止开发",
        "请修改副本；禁止开发",
        "请修改副本，不要修改任何代码",
        "请修改副本，不修改测试或业务代码",
        "请修改副本，不要修改原件和副本",
        "请修改入口，不要修改测试代码和任何业务代码",
        "请修改入口，不要修改Tests.cs或任何其他文件",
        "请修复入口，先讨论。不要修改测试。",
        "请修改Tests.cs，不要修改Tests.cs",
        "请修改测试，不要修改测试",
        "请在隔离副本修改原件，不要修改原件",
        "只要新增方案",
        "继续\n此前已授权的请求：请修复返回值，先给我方案",
        "开始吧\n此前已授权的请求：请修复返回值，不要修改代码",
        "开始吧\n此前已授权的请求：如何新增一个方法",
    ],
)
async def test_questions_and_unrevoked_negatives_cannot_create(runtime, prompt):
    result = await tools(runtime, prompt)["create_code_change"].ainvoke({"title": "x", "goal": "x"})
    assert "尚未要求修改" in result
    assert runtime.code_changes.list() == []


async def test_existing_change_contract_is_read_before_edit_and_scope_is_enforced(runtime):
    changes = runtime.code_changes
    change = changes.create(
        "入口",
        "保持入口可读",
        acceptance_criteria=["入口可读"],
        constraints="不得联网",
        allowed_paths=["Program.cs"],
    )
    current = changes.read_file(change["id"], "Program.cs")
    bound = tools(runtime, "请修改入口")
    arguments = {
        "change_id": change["id"],
        "path": "Program.cs",
        "before": current["content"],
        "after": current["content"] + "// changed",
        "version": current["version"],
    }
    assert "请先读取副本" in await bound["edit_change_file"].ainvoke(arguments)
    read = json.loads(
        await bound["read_change_file"].ainvoke({"change_id": change["id"], "path": "Program.cs"})
    )
    assert read["contract"]["constraints"] == "不得联网"
    assert read["contract"]["acceptance_criteria"] == ["入口可读"]
    assert read["contract"]["allowed_paths"] == ["Program.cs"]
    edited = json.loads(await bound["edit_change_file"].ainvoke(arguments))
    assert edited["status"] == "editing"
    diff = json.loads(await bound["get_change_diff"].ainvoke({"change_id": change["id"]}))
    assert diff["contract"]["goal"] == "保持入口可读" and "+// changed" in diff["diff"]
    rejected = await bound["edit_change_file"].ainvoke(
        {**arguments, "path": "outside.cs", "before": "", "version": ""}
    )
    assert "不在本次需求约定" in rejected


@pytest.mark.parametrize("prompt", ["开始吧", "好的开始吧", "继续", "可以，动手吧"])
def test_analysis_policy_keeps_original_user_question_for_explicit_continuation(prompt):
    from app.core.config import AppSettings

    prior = {"question": "请修复返回值，先给方案", "mode": "deep"}
    policy = analysis_policy(AppSettings(), prompt, prior)
    assert policy["continuing"] and policy["question"] == prior["question"]


async def test_agent_waiting_for_project_lock_cannot_edit_after_contract_changes(runtime):
    changes = runtime.code_changes
    change = changes.create("入口", "只改入口", acceptance_criteria=["可读"])
    bound = tools(runtime, "请修改入口")
    loaded = json.loads(
        await bound["read_change_file"].ainvoke({"change_id": change["id"], "path": "Program.cs"})
    )
    async with runtime.project_lock:
        pending = asyncio.create_task(
            bound["edit_change_file"].ainvoke(
                {
                    "change_id": change["id"],
                    "path": "Program.cs",
                    "before": loaded["content"],
                    "after": loaded["content"] + "// edit",
                    "version": loaded["version"],
                }
            )
        )
        await asyncio.sleep(0.02)
        changes.update_requirements(
            change["id"],
            change["change_version"],
            change["requirements_version"],
            title=change["title"],
            goal=change["goal"],
            acceptance_criteria=["新的验收"],
            constraints="必须先复核",
            allowed_paths=[],
        )
    denied = await pending
    assert "需求约定已变化" in denied
    assert changes.read_file(change["id"], "Program.cs")["content"] == loaded["content"]
    assert changes.diff(change["id"])["files"] == []


async def test_create_never_silently_remembers_a_contract_absent_from_its_result(
    runtime, monkeypatch
):
    changes = runtime.code_changes
    create = changes.create

    def concurrent_update(*args, **kwargs):
        result = create(*args, **kwargs)
        changes.update_requirements(
            result["id"],
            result["change_version"],
            result["requirements_version"],
            title=result["title"],
            goal=result["goal"],
            acceptance_criteria=["new"],
            constraints="不可沿用旧需求",
            allowed_paths=[],
        )
        return result

    monkeypatch.setattr(changes, "create", concurrent_update)
    bound = tools(runtime, "请修改入口")
    created = json.loads(
        await bound["create_code_change"].ainvoke({"title": "入口", "goal": "修改入口"})
    )
    assert created["constraints"] == ""
    file = changes.read_file(created["id"], "Program.cs")
    denied = await bound["edit_change_file"].ainvoke(
        {
            "change_id": created["id"],
            "path": "Program.cs",
            "before": file["content"],
            "after": "changed",
            "version": file["version"],
        }
    )
    assert "需求约定已变化" in denied
    assert changes.diff(created["id"])["files"] == []
