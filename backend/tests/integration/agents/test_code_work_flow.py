"""隔离真实文件与命令，替换外部模型，验证失败反馈确实进入下一轮修复。"""

import asyncio
import json
import sys
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.analysis.retrieval_budget import RetrievalBudget
from app.agents.runtime.project_analyzer import ModelReadingAnalyzer
from app.agents.tools.engineering import engineering_tools
from app.main import create_app
from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus
from tests.helpers.accounts import sign_in
from tests.helpers.models import DeterministicModel


def project_client(client, paths):
    project = client.post(
        "/api/projects",
        json={
            "name": "代码工作测试",
            "source_root": str(paths.workspace),
        },
    ).json()
    return project["id"], f"/api/p/{project['id']}"


def wait_change(client, url, identifier):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        row = client.get(f"{url}/code-changes/{identifier}").json()
        if row["status"] != "verifying":
            return row
        time.sleep(0.02)
    pytest.fail("临时命令没有在期限内完成")


class RepairModel(DeterministicModel):
    profile_id: str

    def _generate(self, messages, stop=None, run_manager=None, **_kwargs):
        outputs = [message for message in messages if isinstance(message, ToolMessage)]
        values = {message.name: json.loads(message.content) for message in outputs}
        if not outputs:
            name, args = "create_code_change", {"title": "修复返回值", "goal": "结果应为2"}
        else:
            last = outputs[-1].name
            identifier = values["create_code_change"]["id"]
            if last == "create_code_change":
                name, args = "read_change_file", {"change_id": identifier, "path": "calc.py"}
            elif last in {"read_change_file", "edit_change_file"}:
                name, args = (
                    "verify_code_change",
                    {
                        "change_id": identifier,
                        "profile_id": self.profile_id,
                    },
                )
            elif last == "verify_code_change":
                verified = values[last]["latest_verification"]
                if verified["status"] == "failed":
                    name, args = (
                        "edit_change_file",
                        {
                            "change_id": identifier,
                            "path": "calc.py",
                            "before": "answer = 1",
                            "after": "answer = 2",
                            "version": values["read_change_file"]["version"],
                        },
                    )
                else:
                    name, args = "get_change_diff", {"change_id": identifier}
            else:
                return ChatResult(
                    generations=[
                        ChatGeneration(
                            message=AIMessage(
                                content="隔离副本已修复，配置测试通过；原文件保持不变。"
                            )
                        )
                    ]
                )
        message = AIMessage(
            content="",
            tool_calls=[
                {
                    "id": f"step-{len(outputs)}",
                    "name": name,
                    "args": args,
                }
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=message)])


@pytest.mark.parametrize(
    ("question", "previous"),
    [
        ("请修复返回值并运行测试", None),
        ("继续", "请修复返回值并运行测试"),
        ("好的开始吧", "请修复返回值并运行测试，先给我方案"),
        ("请在隔离副本修改calc.py，将answer改为2，检查差异，不改原件", None),
    ],
)
async def test_agent_reads_failed_exit_then_repairs_and_reverifies_original_unchanged(
    services,
    monkeypatch,
    question,
    previous,
):
    from app.bootstrap import create_services

    paths = services[0]
    original = paths.workspace / "calc.py"
    original.write_text("answer = 1\n", encoding="utf-8")
    original_bytes = original.read_bytes()
    app_services = create_services(paths)
    runtime = app_services.runtime
    runtime.repository.project_id = "test-code-project"
    changes = runtime.code_changes
    profile = changes.save_profile(
        "结果校验",
        [
            sys.executable,
            "-c",
            "from pathlib import Path; namespace = {}; "
            "exec(Path('calc.py').read_text(encoding='utf-8-sig'), namespace); "
            "assert namespace['answer'] == 2, 'answer must equal 2'",
        ],
    )
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_, **_kw: RepairModel(profile_id=profile["id"]),
    )
    owned = []
    try:
        async with AsyncSqliteSaver.from_conn_string(
            str(paths.data / "test-checkpoints.db")
        ) as saver:
            graph = await runtime.graph(
                "test-flow",
                saver,
                lambda *_: None,
                owned,
                question_text=question,
                policy={
                    "continuing": True,
                    "question": previous,
                    "mode": "standard",
                    "limit": 24,
                    "reserve": 0,
                }
                if previous
                else None,
                memory_query="返回值",
                source_options={"use_memory": False, "use_knowledge": False, "use_deepwiki": False},
            )
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content="请修复返回值")]},
                {"configurable": {"thread_id": "test-flow"}, "recursion_limit": 40},
            )
        results = [
            json.loads(message.content)
            for message in result["messages"]
            if isinstance(message, ToolMessage) and message.name == "verify_code_change"
        ]
        assert [row["latest_verification"]["status"] for row in results] == ["failed", "passed"]
        assert results[0]["latest_verification"]["exit_code"] == 1
        assert "answer must equal 2" in results[0]["latest_verification"]["output"]
        assert results[1]["latest_verification"]["exit_code"] == 0
        assert original.read_bytes() == original_bytes
        assert "+answer = 2" in changes.export(results[-1]["id"])
    finally:
        await changes.shutdown()
        runtime.semantic.close()
        app_services.database.close()


def test_confirmed_experience_keeps_fixed_change_and_verification_then_is_recalled(
    services, monkeypatch
):
    paths = services[0]
    with TestClient(create_app(paths)) as client:
        _, url = project_client(client, paths)
        change = client.post(
            f"{url}/code-changes", json={"title": "入口校验", "goal": "单元验证"}
        ).json()
        profile = client.post(
            f"{url}/code-changes/profiles",
            json={
                "name": "临时校验",
                "argv": [sys.executable, "-c", "print('passed')"],
                "executor": {"kind": "trusted_host"},
            },
        ).json()
        client.post(f"{url}/code-changes/{change['id']}/verify", json={"profile_id": profile["id"]})
        change = wait_change(client, url, change["id"])
        verified = change["latest_verification"]
        body = {
            "title": "E907 参数解析问题",
            "verification_id": verified["id"],
            "change_version": verified["change_version"],
            "payload": {
                "problem": "E907 参数解析问题",
                "solution": "补充参数边界检查",
                "verification": "临时配置命令退出码0；尚未进行设备验证",
                "resolution_status": "open",
                "device": "TEST-DEVICE",
                "module": "参数解析",
            },
        }
        response = client.post(f"{url}/code-changes/{change['id']}/experience", json=body)
        assert response.status_code == 201, response.text
        row = response.json()
        assert row["payload"]["source_change_id"] == change["id"]
        assert row["payload"]["source_verification_id"] == verified["id"]
        assert row["payload"]["resolution_status"] == "open"
        again = client.post(f"{url}/code-changes/{change['id']}/experience", json=body).json()
        assert again["id"] == row["id"] and again["version"] == row["version"]
        corpus = DebugIssueCorpus(client.app.state.auth.database)
        hits = corpus.search("E907 参数解析")
        assert hits[0]["id"] == row["id"] and hits[0]["version"] == row["version"]
        runtime = (
            client.app.state.projects.services(change["project_id"]).runtime
            if ("project_id" in change)
            else client.app.state.projects.services(url.split("/")[-1]).runtime
        )
        changes = runtime.code_changes
        actual_diff = changes.diff

        def external_edit_during_diff(identifier):
            with changes.database.session() as session:
                record = changes._row(session, identifier)
                target = changes._work(record) / "external.txt"
            target.write_bytes(b"external change")
            return actual_diff(identifier)

        with monkeypatch.context() as patch:
            patch.setattr(changes, "diff", external_edit_during_diff)
            rejected = client.post(f"{url}/code-changes/{change['id']}/experience", json=body)
            assert rejected.status_code == 409 and "副本版本已变化" in rejected.json()["detail"]
        file = client.get(
            f"{url}/code-changes/{change['id']}/file", params={"path": "Program.cs"}
        ).json()
        client.patch(
            f"{url}/code-changes/{change['id']}/file",
            json={
                "path": "Program.cs",
                "before": file["content"],
                "after": file["content"] + "// change",
                "version": file["version"],
                "requirements_version": file["requirements_version"],
            },
        )
        assert (
            client.post(f"{url}/code-changes/{change['id']}/experience", json=body).status_code
            == 409
        )


def test_new_project_endpoints_obey_ownership_and_admin_command_configuration(services):
    with TestClient(create_app(services[0])) as client:
        _, admin_url = project_client(client, services[0])
        sign_in(client, "user")
        _, user_url = project_client(client, services[0])
        for path in ("/project-reading", "/code-changes", "/code-changes/profiles"):
            assert client.get(admin_url + path).status_code == 404
        response = client.post(
            user_url + "/code-changes/profiles",
            json={
                "name": "不允许",
                "argv": [sys.executable, "-c", "print(1)"],
                "executor": {"kind": "trusted_host"},
            },
        )
        assert response.status_code == 403
        assert client.get("/api/p/independent/code-changes").status_code == 404


def test_project_cannot_rebind_archive_or_delete_while_reading_or_verifying(services, tmp_path):
    paths = services[0]
    other = tmp_path / "new-source"
    other.mkdir()
    with TestClient(create_app(paths)) as client:
        identifier, url = project_client(client, paths)
        runtime = client.app.state.projects.services(identifier).runtime

        async def blocked(_text, _metadata):
            await asyncio.sleep(3600)

        runtime.project_reading.analyzer = blocked
        job = client.post(f"{url}/project-reading", json={}).json()
        assert client.post(f"{url}/project-reading/{job['id']}/start").status_code == 200
        assert client.post("/api/backup").status_code == 409

        def rejected():
            for body in ({"source_root": str(other)}, {"state": "archived"}):
                response = client.patch(f"/api/projects/{identifier}", json=body)
                assert response.status_code == 409, response.text
            assert client.delete(f"/api/projects/{identifier}").status_code == 409

        rejected()
        client.post(f"{url}/project-reading/{job['id']}/pause")
        change = client.post(
            f"{url}/code-changes", json={"title": "生命周期", "goal": "取消测试"}
        ).json()
        profile = client.post(
            f"{url}/code-changes/profiles",
            json={
                "name": "等待取消",
                "argv": [sys.executable, "-c", "import time; time.sleep(30)"],
                "executor": {"kind": "trusted_host"},
            },
        ).json()
        assert (
            client.post(
                f"{url}/code-changes/{change['id']}/verify", json={"profile_id": profile["id"]}
            ).status_code
            == 200
        )
        rejected()
        assert client.post("/api/backup").status_code == 409
        assert client.post(f"{url}/code-changes/{change['id']}/cancel").status_code == 200
        wait_change(client, url, change["id"])
        assert (
            client.patch(f"/api/projects/{identifier}", json={"state": "archived"}).status_code
            == 200
        )
        # 归档后仍可读，不能越过UI直接写入或再次启动后台工作。
        assert client.get(f"{url}/code-changes").status_code == 200
        assert (
            client.post(f"{url}/code-changes", json={"title": "x", "goal": "x"}).status_code == 409
        )
        assert client.post(f"{url}/project-reading/{job['id']}/start").status_code == 409


async def test_engineering_budget_survives_exhausted_search_then_stops_its_own_calls():
    budget = RetrievalBudget(lambda *_: None, max_calls=0)
    calls = []

    async def handler(request):
        calls.append(request.tool_call["id"])
        return ToolMessage(content="passed", tool_call_id=request.tool_call["id"])

    for index in range(21):
        result = await budget.awrap_tool_call(
            SimpleNamespace(
                tool_call={
                    "id": str(index),
                    "name": "verify_code_change",
                }
            ),
            handler,
        )
    assert len(calls) == 20 and result.additional_kwargs["skip_reason"] == "engineering_limit"
    tool = SimpleNamespace(name="get_change_diff")
    request = ModelRequest(
        model=DeterministicModel(), messages=[], tools=[tool], state={"messages": []}, runtime=None
    )
    fresh = RetrievalBudget(lambda *_: None, max_calls=0)

    async def inspect(current):
        return current

    bound = await fresh.awrap_model_call(request, inspect)
    assert bound.tools == [tool] and bound.tool_choice != "none"


@pytest.mark.parametrize(
    "question",
    [
        "分析入口代码",
        "先给修复方案，不要修改",
        "不需要通读项目",
        "通读项目先讨论不开始",
        "请解释这个实现为什么异常",
    ],
)
async def test_analysis_only_tools_do_not_create_or_modify_isolated_copy(services, question):
    from app.bootstrap import create_services

    current = create_services(services[0])
    current.repository.project_id = "project"
    tools = {item.name: item for item in engineering_tools(current.runtime, question)}
    result = await tools["create_code_change"].ainvoke({"title": "x", "goal": "x"})
    assert "尚未要求修改" in result and current.runtime.code_changes.list() == []
    reading = await tools["start_project_reading"].ainvoke({})
    assert "没有要求启动" in reading and current.runtime.project_reading.list()["jobs"] == []
    current.runtime.semantic.close()
    current.database.close()


async def test_reading_model_structure_error_is_redacted_and_resources_closed(
    services, monkeypatch
):
    store = services[-1]
    from app.core.config import ModelSettings

    settings = SimpleNamespace(
        model=ModelSettings(
            base_url="http://invalid.test", model="test", api_key="private-test-key"
        )
    )
    monkeypatch.setattr(
        "app.agents.runtime.project_analyzer.current_configuration", lambda _: settings
    )
    closed = []

    class Model:
        async def ainvoke(self, _messages):
            raise RuntimeError("network private-test-key failed")

    async def close(models):
        closed.extend(models)

    monkeypatch.setattr("app.agents.runtime.project_analyzer.create_model", lambda _: Model())
    monkeypatch.setattr("app.agents.runtime.project_analyzer.close_models", close)
    with pytest.raises(ValueError, match="密钥已隐藏") as error:
        await ModelReadingAnalyzer(store)("class A {}", {"path": "A.cs"})
    assert "private-test-key" not in str(error.value) and len(closed) == 1
