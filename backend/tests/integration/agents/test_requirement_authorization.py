"""真实副本和SQLite核对：代码授权不能被模型用来改写验收与范围。"""

import json

import pytest

from app.agents.tools.engineering import engineering_tools
from app.modules.code_changes import CodeChanges
from app.modules.source_analysis.evidence import SourceEvidence
from app.modules.source_analysis.review import review_answer
from tests.helpers.reviews import CapturingReviewer


@pytest.fixture
def runtime(services):
    from app.bootstrap import create_services

    current = create_services(services[0])
    current.repository.project_id = "requirement-authorization"
    yield current.runtime
    current.runtime.semantic.close()
    current.database.close()


def toolset(runtime, request, evidence=None):
    return {tool.name: tool for tool in engineering_tools(runtime, request, evidence=evidence)}


def revision_args(change, **updates):
    fields = (
        "title",
        "goal",
        "acceptance_criteria",
        "constraints",
        "allowed_paths",
        "change_version",
        "requirements_version",
    )
    return {"change_id": change["id"], **{key: change[key] for key in fields}, **updates}


async def observe(tools, identifier):
    return json.loads(await tools["get_change_diff"].ainvoke({"change_id": identifier}))


async def test_code_repair_permission_cannot_weaken_contract(runtime):
    changes = runtime.code_changes
    created = changes.create(
        "入口",
        "返回2",
        acceptance_criteria=["必须返回2"],
        constraints="不许修改测试",
        allowed_paths=["Program.cs"],
    )
    tools = toolset(runtime, "请修复入口代码")
    await observe(tools, created["id"])

    result = await tools["update_code_change_requirements"].ainvoke(
        revision_args(created, acceptance_criteria=[], constraints="", allowed_paths=[])
    )

    current = changes.get(created["id"])
    assert current["requirements_version"] == created["requirements_version"], result
    assert current["acceptance_criteria"] == ["必须返回2"]
    assert current["constraints"] == "不许修改测试"
    assert current["allowed_paths"] == ["Program.cs"]
    assert "没有明确要求修改需求约定" in result


async def test_contract_only_request_cannot_edit_code(runtime):
    changes = runtime.code_changes
    created = changes.create("入口", "返回2")
    tools = toolset(runtime, "请补充验收标准")
    loaded = json.loads(
        await tools["read_change_file"].ainvoke({"change_id": created["id"], "path": "Program.cs"})
    )
    result = await tools["edit_change_file"].ainvoke(
        {
            "change_id": created["id"],
            "path": "Program.cs",
            "version": loaded["version"],
            "before": loaded["content"],
            "after": "// should not be saved",
        }
    )

    assert changes.read_file(created["id"], "Program.cs")["content"] == loaded["content"], result
    assert changes.diff(created["id"])["files"] == []
    assert "没有要求修改代码" in result
    verification = await tools["verify_code_change"].ainvoke(
        {
            "change_id": created["id"],
            "profile_id": "not-a-command",
        }
    )
    assert "没有要求实施修改" in verification
    assert changes.verification_history(created["id"])["verifications"] == []


async def test_explicit_criteria_revision_preserves_original_request_and_rejects_scope_expansion(
    runtime,
):
    evidence = SourceEvidence(runtime.workspace, lambda *_: None)
    evidence.request_identity = {"message_id": "human-message", "run_id": "run-1"}
    request = "请在隔离副本修复入口，只允许修改Program.cs，不能改测试。"
    tools = toolset(runtime, request, evidence)
    created = json.loads(
        await tools["create_code_change"].ainvoke(
            {
                "title": "入口",
                "goal": "返回2",
                "acceptance_criteria": ["返回2"],
                "constraints": "不能改测试",
                "allowed_paths": ["Program.cs"],
            }
        )
    )
    binding = created["request_binding"]
    assert binding["original"]["origin"] == {
        "channel": "chat",
        "text": request,
        "message_id": "human-message",
        "run_id": "run-1",
        "actor_id": "",
    }
    assert binding["original"]["contract"]["allowed_paths"] == ["Program.cs"]
    assert binding["revisions"] == []
    assert "request_origin" not in tools["create_code_change"].args

    revision_request = "请补充验收标准，不要修改代码"
    revisions = toolset(runtime, revision_request, evidence)
    await observe(revisions, created["id"])
    for unrequested in (
        {"allowed_paths": []},
        {"constraints": ""},
        {"goal": "返回1"},
        {"title": "放宽"},
    ):
        result = await revisions["update_code_change_requirements"].ainvoke(
            revision_args(created, acceptance_criteria=["返回2", "原件不变"], **unrequested)
        )
        assert "用户未授权修改这些需求字段" in result
        assert runtime.code_changes.get(created["id"]) == created

    updated = json.loads(
        await revisions["update_code_change_requirements"].ainvoke(
            revision_args(created, acceptance_criteria=["返回2", "原件不变"])
        )
    )
    assert updated["request_binding"]["original"] == binding["original"]
    (revision,) = updated["request_binding"]["revisions"]
    assert revision["changes"] == {"acceptance_criteria": ["返回2", "原件不变"]}
    assert revision["origin"]["text"] == revision_request
    assert revision["previous_requirements_version"] == created["requirements_version"]
    assert updated["requirements_version"] != created["requirements_version"]
    assert updated["change_version"] == created["change_version"]
    assert runtime.code_changes.diff(created["id"])["files"] == []

    reopened = CodeChanges(
        runtime.paths, runtime.repository.database, runtime.workspace, runtime.repository.project_id
    )
    assert reopened.get(created["id"])["request_binding"] == updated["request_binding"]
    reviewer = CapturingReviewer()
    await review_answer(reviewer, evidence, "副本尚未修改，验收标准已补充。")
    (payload,) = reviewer.requests
    assert payload["user_request"] == revision_request
    assert payload["code_work"]["changes"][0]["request_binding"] == updated["request_binding"]
    assert payload["code_work"]["changes"][0]["verifications"] == []


async def test_full_contract_revision_is_explicit_and_legacy_origin_stays_unknown(runtime):
    changes = runtime.code_changes
    created = changes.create("旧副本", "旧目标", allowed_paths=["Program.cs"])
    assert created["request_binding"] is None
    tools = toolset(runtime, "请更新需求约定")
    await observe(tools, created["id"])
    result = json.loads(
        await tools["update_code_change_requirements"].ainvoke(
            revision_args(
                created,
                title="新标题",
                goal="新目标",
                acceptance_criteria=["可读"],
                constraints="离线",
                allowed_paths=["*.cs"],
            )
        )
    )
    assert result["title"] == "新标题" and result["goal"] == "新目标"
    assert result["constraints"] == "离线" and result["allowed_paths"] == ["*.cs"]
    assert result["request_binding"]["original"] is None
    assert set(result["request_binding"]["revisions"][0]["changes"]) == {
        "title",
        "goal",
        "acceptance_criteria",
        "constraints",
        "allowed_paths",
    }

    # 标准化后无变化不追加历史，也不能让已有验证凭空失效。
    await observe(tools, created["id"])
    no_op = json.loads(
        await tools["update_code_change_requirements"].ainvoke(
            revision_args(result, title="  新标题  ", acceptance_criteria=[" 可读 ", "可读", ""])
        )
    )
    assert no_op == result
    changed = changes.update_requirements(
        result["id"],
        result["change_version"],
        result["requirements_version"],
        title=result["title"],
        goal=result["goal"],
        acceptance_criteria=["新条件"],
        constraints=result["constraints"],
        allowed_paths=result["allowed_paths"],
    )
    assert changed["request_binding"]["original"] is None
    assert changed["request_binding"]["revisions"][-1]["origin"] is None


async def test_refused_revision_is_atomic_when_waiting_for_project_lock(runtime):
    import asyncio

    changes = runtime.code_changes
    created = changes.create("入口", "原目标", allowed_paths=["Program.cs"])
    tools = toolset(runtime, "请补充验收标准")
    await observe(tools, created["id"])
    async with runtime.project_lock:
        pending = asyncio.create_task(
            tools["update_code_change_requirements"].ainvoke(
                revision_args(created, acceptance_criteria=["可读"])
            )
        )
        await asyncio.sleep(0.02)
        changed = changes.update_requirements(
            created["id"],
            created["change_version"],
            created["requirements_version"],
            title=created["title"],
            goal="并发人工目标",
            allowed_paths=["Program.cs"],
        )
    assert "副本或需求已变化" in await pending
    assert changes.get(created["id"]) == changed
