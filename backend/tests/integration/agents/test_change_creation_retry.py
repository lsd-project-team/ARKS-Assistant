"""同一人类请求重试创建时保留副本，不能通过换新副本重置验收范围。"""

import asyncio
import json
import sys

import pytest

from app.agents.tools.engineering import engineering_tools
from app.infrastructure.database.session import Database
from app.modules.code_changes import CodeChanges
from app.modules.code_changes.request_binding import RequestOrigin
from app.modules.source_analysis.evidence import SourceEvidence


@pytest.fixture
def runtime(services):
    from app.bootstrap import create_services

    current = create_services(services[0])
    current.repository.project_id = "creation-retry-project"
    yield current.runtime
    current.runtime.semantic.close()
    current.database.close()


def bound_tools(runtime, *, message_id="human-message", run_id="run-1"):
    evidence = SourceEvidence(runtime.workspace, lambda *_: None)
    evidence.request_identity = {"message_id": message_id, "run_id": run_id}
    return {
        item.name: item
        for item in engineering_tools(
            runtime,
            "请修复隔离副本入口，只允许修改Program.cs",
            evidence=evidence,
        )
    }


CONTRACT = {
    "title": "修复入口",
    "goal": "保留入口",
    "acceptance_criteria": ["入口仍可读"],
    "constraints": "不得修改测试",
    "allowed_paths": ["Program.cs"],
}


async def create(tools, **updates):
    return json.loads(await tools["create_code_change"].ainvoke({**CONTRACT, **updates}))


async def test_repeated_create_cannot_start_a_new_copy_with_weaker_contract(runtime):
    tools = bound_tools(runtime)
    first = await create(tools)
    before = runtime.code_changes.read_file(first["id"], "Program.cs")
    runtime.code_changes.edit_file(first["id"], "Program.cs", "Main", "Start", before["version"])
    current = runtime.code_changes.get(first["id"])

    retried = await create(tools, acceptance_criteria=[], constraints="", allowed_paths=[])

    assert retried["id"] == first["id"]
    assert retried["requirements_version"] == current["requirements_version"]
    assert retried["request_binding"] == current["request_binding"]
    assert retried["acceptance_criteria"] == ["入口仍可读"]
    assert retried["constraints"] == "不得修改测试"
    assert retried["allowed_paths"] == ["Program.cs"]
    assert retried["change_version"] == current["change_version"]
    assert "Start" in runtime.code_changes.read_file(first["id"], "Program.cs")["content"]
    assert retried["reused"] is True
    assert len(runtime.code_changes.list()) == 1


async def test_parallel_factories_for_same_message_share_one_creation(runtime):
    a, b = bound_tools(runtime), bound_tools(runtime, run_id="run-2")

    first, second = await asyncio.gather(create(a), create(b))

    assert first["id"] == second["id"]
    assert first["allowed_paths"] == second["allowed_paths"] == ["Program.cs"]
    assert len(runtime.code_changes.list()) == 1


async def test_reopened_database_reuses_latest_contract_without_resetting_it(runtime):
    first = await create(bound_tools(runtime))
    current = runtime.code_changes.update_requirements(
        first["id"],
        first["change_version"],
        first["requirements_version"],
        **{**CONTRACT, "acceptance_criteria": ["入口仍可读", "不得联网"]},
        request_origin=RequestOrigin("manual_form", "增加验收标准", actor_id="test-actor"),
        authorized_fields={"acceptance_criteria"},
    )
    origin = first["request_binding"]["original"]["origin"]
    runtime.repository.database.close()
    reopened = Database(runtime.paths.data / "app.sqlite3")
    try:
        changes = CodeChanges(
            runtime.paths, reopened, runtime.workspace, runtime.repository.project_id
        )
        retried = changes.create(
            **{**CONTRACT, "acceptance_criteria": [], "constraints": "", "allowed_paths": []},
            request_origin=RequestOrigin(**{**origin, "run_id": "resumed-run"}),
        )
        assert retried["id"] == current["id"] and retried["reused"]
        assert retried["requirements_version"] == current["requirements_version"]
        assert retried["request_binding"] == current["request_binding"]
        assert retried["acceptance_criteria"] == ["入口仍可读", "不得联网"]
        assert len(changes.list()) == 1
    finally:
        reopened.close()


async def test_discarded_request_copy_cannot_be_recreated_by_the_model(runtime):
    first = await create(bound_tools(runtime))
    runtime.code_changes.discard(first["id"])

    tools = bound_tools(runtime, run_id="resumed-run")
    result = await tools["create_code_change"].ainvoke(CONTRACT)

    assert "本次请求的副本已丢弃或清理" in result
    assert len(runtime.code_changes.list()) == 1
    assert runtime.code_changes.get(first["id"])["status"] == "discarded"


async def test_explicit_new_human_request_and_manual_form_keep_separate_copies(runtime):
    first = await create(bound_tools(runtime))
    second = await create(bound_tools(runtime, message_id="new-human-message"))
    assert first["id"] != second["id"]
    original = first["request_binding"]["original"]["origin"]
    edited_message = runtime.code_changes.create(
        **CONTRACT,
        request_origin=RequestOrigin(**{**original, "text": "请修改另一个目标"}),
    )
    assert edited_message["id"] not in {first["id"], second["id"]}
    manual = RequestOrigin("manual_form", "人工创建", actor_id="test-actor")
    a = runtime.code_changes.create(**CONTRACT, request_origin=manual)
    b = runtime.code_changes.create(**CONTRACT, request_origin=manual)
    assert a["id"] != b["id"]
    assert len(runtime.code_changes.list()) == 5


async def test_same_message_identity_in_another_project_cannot_reuse_private_copy(runtime):
    first = await create(bound_tools(runtime))
    runtime.repository.project_id = "different-project"

    second = await create(bound_tools(runtime))

    assert second["id"] != first["id"]
    assert len(runtime.code_changes.list()) == 1
    assert runtime.code_changes.list()[0]["id"] == second["id"]


async def test_direct_tool_factory_without_message_identity_still_reuses_its_first_copy(runtime):
    tools = {item.name: item for item in engineering_tools(runtime, "请修改入口")}
    first = await create(tools)

    retried = await create(tools, allowed_paths=[])

    assert retried["id"] == first["id"] and retried["reused"]
    assert retried["allowed_paths"] == ["Program.cs"]
    assert retried["request_binding"]["original"]["origin"]["message_id"] == ""
    assert len(runtime.code_changes.list()) == 1


async def test_retry_retains_real_command_proof_for_the_current_edited_copy(runtime):
    tools = bound_tools(runtime)
    first = await create(tools)
    loaded = runtime.code_changes.read_file(first["id"], "Program.cs")
    runtime.code_changes.edit_file(first["id"], "Program.cs", "Main", "Start", loaded["version"])
    profile = runtime.code_changes.save_profile(
        "副本入口检查",
        [
            sys.executable,
            "-I",
            "-c",
            "from pathlib import Path; "
            "assert 'void Start()' in Path('Program.cs').read_text(); print('copy-verified')",
        ],
        category="test",
        executor={"kind": "trusted_host"},
    )
    verified = json.loads(
        await tools["verify_code_change"].ainvoke(
            {
                "change_id": first["id"],
                "profile_id": profile["id"],
            }
        )
    )
    proof = verified["latest_verification"]
    assert proof["status"] == "passed" and proof["exit_code"] == 0

    retried = await create(bound_tools(runtime, run_id="resumed-run"), allowed_paths=[])

    assert retried["id"] == first["id"] and retried["status"] == "passed"
    assert retried["change_version"] == verified["change_version"]
    assert retried["requirements_version"] == verified["requirements_version"]
    assert retried["latest_verification"] == proof and not proof["stale"]
    assert "copy-verified" in proof["output"]
    assert "void Main()" in (runtime.workspace.root / "Program.cs").read_text()
    assert len(runtime.code_changes.verification_history(first["id"])["verifications"]) == 1


async def test_resumed_agent_cannot_replace_bound_copy_via_a_fresh_create_call(
    runtime, monkeypatch
):
    from langchain_core.messages import AIMessage, ToolMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    from app.modules.projects.models import Project
    from tests.helpers.models import DeterministicModel

    repository = runtime.repository
    with repository.database.session.begin() as session:
        session.add(
            Project(
                id=repository.project_id, name="创建重试", source_root=str(runtime.workspace.root)
            )
        )
    question = "请修复隔离副本入口，只允许修改Program.cs"
    previous = repository.create_run(
        None,
        question,
        [],
        {
            "use_memory": False,
            "use_knowledge": False,
            "use_deepwiki": False,
        },
    )
    first = await create(
        bound_tools(runtime, message_id=previous["message_id"], run_id=previous["id"])
    )
    loaded = runtime.code_changes.read_file(first["id"], "Program.cs")
    runtime.code_changes.edit_file(first["id"], "Program.cs", "Main", "Start", loaded["version"])
    repository.event(previous["id"], "code_change_reference", {"id": first["id"]})
    repository.set_status(previous["id"], "interrupted")
    resumed = repository.resume(previous["id"])

    class RetryModel(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if "独立的源码结论复核器" in messages[0].text:
                reply = AIMessage(content='{"verdict":"passed","issues":[]}')
            elif not any(
                isinstance(item, ToolMessage) and item.name == "create_code_change"
                for item in messages
            ):
                reply = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "retry-create",
                            "name": "create_code_change",
                            "args": {
                                **CONTRACT,
                                "acceptance_criteria": [],
                                "constraints": "",
                                "allowed_paths": [],
                            },
                        }
                    ],
                )
            else:
                result = json.loads(
                    next(
                        item.text
                        for item in reversed(messages)
                        if isinstance(item, ToolMessage) and item.name == "create_code_change"
                    )
                )
                assert result["id"] == first["id"] and result["reused"]
                assert result["allowed_paths"] == ["Program.cs"]
                reply = AIMessage(content="沿用已有副本，当前差异保留，尚未验证。")
            return ChatResult(generations=[ChatGeneration(message=reply)])

    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_a, **_kw: RetryModel()
    )
    answer = await runtime.execute(
        resumed, lambda kind, payload: repository.event(resumed["id"], kind, payload)
    )

    assert "沿用已有副本" in answer
    assert len(runtime.code_changes.list()) == 1
    current = runtime.code_changes.get(first["id"])
    origin = current["request_binding"]["original"]["origin"]
    assert origin["message_id"] == resumed["message_id"] == previous["message_id"]
    assert origin["run_id"] == previous["id"] != resumed["id"]
    assert origin["text"] == question and current["allowed_paths"] == ["Program.cs"]
    assert current["acceptance_criteria"] == ["入口仍可读"]
    assert current["constraints"] == "不得修改测试"
    assert "Start" in runtime.code_changes.read_file(first["id"], "Program.cs")["content"]
    assert current["latest_verification"] is None and current["review"] is None
