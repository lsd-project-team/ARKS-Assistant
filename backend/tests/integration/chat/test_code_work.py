"""新代码副本 API 的认证、对话归属和 Agent 工具闭环。"""

import io
import json
import re
import zipfile

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.agents.runtime.engine import AgentRuntime
from app.main import create_app
from app.modules.chat.schemas import SourceOptions
from tests.helpers.accounts import sign_in
from tests.helpers.api_paths import project_api
from tests.helpers.code_work import FILE, make_work
from tests.helpers.models import DeterministicModel


@pytest.fixture
def work(services, tmp_path):
    return make_work(services, tmp_path)


class EditingModel(DeterministicModel):
    file_path: str = FILE
    calls_seen: list[str] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tools = [message for message in messages if isinstance(message, ToolMessage)]
        last = tools[-1] if tools else None
        args = {}
        if last is None:
            name = "prepare_code_workspace"
        elif last.name == "prepare_code_workspace":
            name, args = "read_work_file", {"path": self.file_path}
        elif last.name == "read_work_file":
            result = json.loads(last.content)
            name, args = (
                "edit_work_file",
                {
                    "path": self.file_path,
                    "old_text": "int Value = 1;",
                    "new_text": "int Value = 2;",
                    "version": result["version"],
                },
            )
        elif last.name == "edit_work_file":
            name = "inspect_work_changes"
        else:
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content="已修改独立副本，差异可在代码修改面板查看。尚未运行仿真。"
                        )
                    )
                ]
            )
        self.calls_seen.append(name)
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[{"id": f"work-{len(tools)}", "name": name, "args": args}],
                    )
                )
            ]
        )


@pytest.mark.parametrize("exhausted_retrieval", [False, True])
@pytest.mark.parametrize("question", ["将 Value 初值改为2", "/修改代码 将 Value 改为2"])
async def test_agent_uses_writable_copy_tools_without_changing_original(
    work, services, monkeypatch, exhausted_retrieval, question
):
    service, _, original = work
    # 首次请求既没有附件，也没有预先创建的副本，不能由旧入口条件碰巧放行。
    thread = services[3].create_thread("直接描述新需求")["id"]
    assert not service.exists(thread)
    model = EditingModel()
    if exhausted_retrieval:
        from app.agents.analysis.retrieval_budget import RetrievalBudget

        monkeypatch.setattr(
            "app.agents.runtime.executor.RetrievalBudget",
            lambda emit, _limit, _reserve, evidence, progress: RetrievalBudget(
                emit, 0, 0, evidence, progress
            ),
        )
        bound_tools = []

        def bind_tools(self, definitions, **options):
            assert options.get("tool_choice") != "none"
            bound_tools.append({tool.name for tool in definitions})
            return self

        monkeypatch.setattr(EditingModel, "bind_tools", bind_tools)
    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *a, **kw: model)
    paths, _, workspace, repository, memories, settings = services
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    run = repository.create_run(
        thread,
        question,
        [],
        SourceOptions(use_memory=False, use_knowledge=False, use_deepwiki=False).model_dump(),
    )
    events = []
    answer = await runtime.execute(run, lambda kind, payload: events.append((kind, payload)))
    assert "已修改独立副本" in answer
    assert model.calls_seen == [
        "prepare_code_workspace",
        "read_work_file",
        "edit_work_file",
        "inspect_work_changes",
    ]
    assert "+ int Value = 2;" in service.diff(thread, FILE)["diff"]
    assert "Value = 1" in (original / "Main/Example.cs").read_text(encoding="utf-8")
    assert any(kind == "code_work" for kind, _ in events)
    if exhausted_retrieval:
        assert bound_tools and all(
            {"read_work_file", "edit_work_file", "verify_code_workspace"} <= tools
            for tools in bound_tools
        )


@pytest.mark.parametrize("configured", [False, True])
async def test_plain_answer_does_not_prepare_or_modify_code_copy(
    services, tmp_path, monkeypatch, configured
):
    if configured:
        make_work(services, tmp_path)
    model = DeterministicModel()
    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *a, **kw: model)
    paths, _, workspace, repository, memories, settings = services
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("只解释")["id"]
    run = repository.create_run(
        thread,
        "请解释重复调用的原因，先不要修改代码",
        [],
        SourceOptions(use_memory=False, use_knowledge=False, use_deepwiki=False).model_dump(),
    )
    events = []
    answer = await runtime.execute(run, lambda kind, payload: events.append((kind, payload)))
    assert answer == "测试回复"
    assert not runtime.code_work.exists(thread)
    assert not runtime.code_work.folder(thread).exists()
    assert not any(kind == "code_work" for kind, _ in events)


def test_api_edits_export_stale_revert_and_deleted_thread_cleanup(work, services):
    service, _, original = work
    with TestClient(create_app(services[0])) as client:
        thread = client.post(project_api(client, "/threads"), json={"title": "副本接口"}).json()[
            "id"
        ]
        prefix = project_api(client, f"/threads/{thread}/code-work")
        assert client.post(prefix).status_code == 200
        assert client.get(prefix + "/summary").json()["files"] == []
        read = client.get(prefix + "/file", params={"path": FILE}).json()
        response = client.put(
            prefix + "/file",
            json={
                "path": FILE,
                "version": read["version"],
                "content": "class Example { int Value = 9; }",
            },
        )
        assert response.status_code == 200
        current = response.json()
        assert current["revision"] == 1
        summary_response = client.get(prefix + "/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["revision"] == 1 and len(summary["files"]) == 1
        assert summary["files"][0]["path"] == FILE
        assert (summary["additions"], summary["deletions"]) == (1, 4)
        assert (
            client.put(
                prefix + "/file",
                json={"path": FILE, "version": read["version"], "content": "stale"},
            ).status_code
            == 409
        )
        difference = client.get(prefix + "/diff", params={"path": FILE}).json()
        assert "int Value = 9;" in difference["after"]
        assert client.get(prefix + "/export?revision=0").status_code == 409
        package = client.get(prefix + "/export?revision=1")
        assert package.status_code == 200
        assert (
            zipfile.ZipFile(io.BytesIO(package.content)).read(FILE)
            == b"class Example { int Value = 9; }"
        )
        assert (
            client.post(
                prefix + "/revert", json={"path": FILE, "version": current["version"]}
            ).json()["files"]
            == []
        )
        folder = service.folder(thread)
        assert client.delete(project_api(client, f"/threads/{thread}")).status_code == 200
        assert client.get(prefix).status_code == 404
        assert client.delete(project_api(client, f"/threads/{thread}/permanent")).status_code == 200
        assert not folder.exists()
    assert "Value = 1" in (original / "Main/Example.cs").read_text(encoding="utf-8")


def test_config_requires_admin_and_missing_thread_is_not_created(services):
    with TestClient(create_app(services[0])) as client:
        assert client.get(project_api(client, "/threads/missing/code-work")).status_code == 404
        assert client.post(project_api(client, "/threads/missing/code-work")).status_code == 404
        environment = client.get("/api/settings/code-work").json()
        assert environment["source_root"] == ""
        assert re.fullmatch(r"[a-f0-9]{64}", environment["version"])
        assert (
            client.put(
                "/api/settings/code-work",
                json={"source_root": "missing", "version": environment["version"]},
            ).status_code
            == 409
        )


@pytest.mark.authentication
def test_other_account_cannot_read_edit_verify_or_export_work(work, services):
    service, _, _ = work
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        project = client.post("/api/projects", json={"name": "私有代码工作"}).json()
        base = f"/api/p/{project['id']}"
        thread = client.post(base + "/threads", json={"title": "私人副本"}).json()["id"]
        prefix = base + f"/threads/{thread}/code-work"
        assert client.post(prefix).status_code == 200
        assert client.get("/api/settings/code-work").status_code == 403
        assert client.put("/api/settings/code-work", json={}).status_code == 403
        # 切换另一名普通用户；已知项目和对话ID也不能绕过归属。
        from tests.helpers.accounts import login_second

        sign_in(client, "admin")
        created = client.post(
            "/api/admin/accounts",
            json={
                "username": "second",
                "display_name": "乙",
                "role": "user",
                "password": "second-pass-123456",
            },
        )
        assert created.status_code in {200, 201}, created.text
        login_second(client)
        for method, suffix in [
            ("GET", ""),
            ("GET", "/summary"),
            ("POST", ""),
            ("GET", "/diff?path=" + FILE),
            ("POST", "/verify"),
            ("POST", "/cancel"),
            ("GET", "/export?revision=0"),
        ]:
            assert client.request(method, prefix + suffix).status_code == 404
