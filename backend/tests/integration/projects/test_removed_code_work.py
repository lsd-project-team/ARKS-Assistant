"""旧修改接口和模型工具退出后，项目与源码读取仍正常。"""

from fastapi.testclient import TestClient
from pydantic import Field

from app.agents.runtime.engine import AgentRuntime
from app.main import create_app
from app.modules.chat.schemas import SourceOptions
from app.modules.projects.models import Project
from tests.helpers.models import DeterministicModel


def test_removed_modification_endpoints_are_unavailable_without_changing_source(services):
    original = services[2].read("Program.cs")
    with TestClient(create_app(services[0])) as client:
        project = client.get("/api/projects").json()["projects"][0]
        base = f"/api/p/{project['id']}"
        for method, suffix in (
            ("GET", "/code-changes"),
            ("POST", "/code-changes"),
            ("GET", "/code-changes/readiness"),
            ("GET", "/code-changes/profiles"),
            ("POST", "/code-changes/profiles"),
            ("PATCH", "/code-changes/old/file"),
            ("POST", "/code-changes/old/verify"),
            ("POST", "/code-changes/old/review"),
            ("POST", "/code-changes/old/delivery"),
            ("POST", "/code-changes/cleanup"),
        ):
            assert client.request(method, base + suffix, json={}).status_code == 404
        source = client.get(base + "/file?path=Program.cs")
        assert source.status_code == 200 and source.json()["version"] == original["version"]
        assert client.post(base + "/threads", json={}).status_code == 201
        assert not hasattr(
            client.app.state.projects.services(project["id"]).runtime, "code_changes"
        )
    assert services[2].read("Program.cs") == original
    assert not (services[0].scratch / "code-changes").exists()


class ToolBoundaryModel(DeterministicModel):
    names: set[str] = Field(default_factory=set)

    def bind_tools(self, tools, **kwargs):
        self.names.update(
            item.get("name", "") if isinstance(item, dict) else item.name for item in tools
        )
        return self


async def test_real_agent_model_receives_read_tools_without_retired_modification_tools(
    services, monkeypatch
):
    paths, database, workspace, repository, memories, settings = services
    with database.session.begin() as session:
        session.add(Project(id=workspace.id, name="只读分析", source_root=str(workspace.root)))
    repository.project_id = workspace.id
    model = ToolBoundaryModel()
    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *a, **kw: model)
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    run = repository.create_run(
        None,
        "你好",
        [],
        SourceOptions(use_memory=False, use_knowledge=False, use_deepwiki=False).model_dump(),
    )
    answer = await runtime.execute(run, lambda *_: None)
    assert answer
    assert {"read_source", "search_source", "read_conversation_message"} <= model.names
    assert (
        not {
            "create_code_change",
            "read_change_file",
            "edit_change_file",
            "get_change_diff",
            "verify_code_change",
            "list_code_changes",
            "list_verification_profiles",
            "update_code_change_requirements",
            "execute",
        }
        & model.names
    )
    assert not (paths.scratch / "code-changes").exists()
    assert workspace.read("Program.cs")["content"].startswith("class Program")
