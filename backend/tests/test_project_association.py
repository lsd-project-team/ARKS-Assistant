"""自动关联依据真实本地 Git 或同目录配置；创建和切换项目保持隔离。"""

import asyncio
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from mcp_types import Tool

from app.api.projects import ProjectCreate
from app.config import AppSettings, McpSettings
from app.main import create_app
from app.mcp_client import adapt_tool
from app.models import SourceWorkspace
from app.project_association import git_repository, repository_name
from app.projects import Projects
from app.run_configuration import current_configuration
from app.services import create_services


def git_source(folder, repo):
    folder.mkdir()
    (folder / "Program.cs").write_text(f"// {repo}\nclass Program {{}}", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(folder)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(folder), "remote", "add", "origin", f"https://github.com/{repo}.git"],
        check=True,
        capture_output=True,
    )
    return folder


@pytest.mark.parametrize(
    "url",
    [
        "https://user:private-test-token@github.com/team/Example.git",
        "git@github.com:team/Example.git",
        "ssh://git@github.com/team/Example.git",
    ],
)
def test_repository_addresses_normalize_without_exposing_credentials(url):
    assert repository_name(url) == "team/Example"
    assert repository_name("https://other.example/team/Example") is None
    assert repository_name("../Example") is None
    assert repository_name("team/Example", allow_bare=False) is None


def test_preview_create_and_source_identity_are_bound_automatically(services, tmp_path):
    root = git_source(tmp_path / "source with spaces", "team/ProjectA")
    with TestClient(create_app(services[0])) as client:
        preview = client.get("/api/projects/association", params={"source_root": str(root)})
        assert preview.status_code == 200 and preview.json()["deepwiki_repo"] == "team/ProjectA"
        created = client.post("/api/projects", json={"name": "自动关联", "source_root": str(root)})
        assert created.status_code == 201
        project = created.json()
        assert project["deepwiki_repo"] == "team/ProjectA"
        app = client.app
        with app.state.projects.database.session() as session:
            from app.workspace import Workspace

            assert session.get(SourceWorkspace, Workspace(root).source_id).root == str(
                root.resolve()
            )
        source = client.get(f"/api/p/{project['id']}/file", params={"path": "Program.cs"})
        assert "team/ProjectA" in source.json()["content"]
        assert (
            client.get(f"/api/projects/{project['id']}").json()["deepwiki_repo"] == "team/ProjectA"
        )


def test_business_subdirectory_never_inherits_application_parent_git(services, tmp_path):
    parent = git_source(tmp_path / "parent", "application/Parent")
    child = parent / "business"
    child.mkdir()
    assert git_repository(str(child)) is None
    with TestClient(create_app(services[0])) as client:
        preview = client.get("/api/projects/association", params={"source_root": str(child)}).json()
        assert preview["status"] == "unknown" and preview["deepwiki_repo"] == ""
        saved = client.post(
            "/api/projects", json={"name": "业务源码", "source_root": str(child)}
        ).json()
        assert saved["source_root"] == str(child) and saved["deepwiki_repo"] == ""


def test_exact_directory_can_reuse_existing_binding_and_workflow_catalogue(services, tmp_path):
    services[-1].save(AppSettings(deepwiki_repo="existing/Trunk"))
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    with TestClient(create_app(services[0])) as client:
        preview = client.get(
            "/api/projects/association", params={"source_root": str(services[0].workspace)}
        ).json()
        assert preview["deepwiki_repo"] == "existing/Trunk" and preview["knowledge_available"]
        project = client.post(
            "/api/projects",
            json={"name": "同源码新项目", "source_root": str(services[0].workspace)},
        ).json()
        assert project["deepwiki_repo"] == "existing/Trunk"
        metadata = client.get(f"/api/projects/{project['id']}").json()
        assert metadata["knowledge_available"]
        assert (
            client.get("/api/projects/association", params={"source_root": str(unrelated)}).json()[
                "deepwiki_repo"
            ]
            == ""
        )


def test_manual_override_and_multiple_source_repositories(services, tmp_path):
    first = git_source(tmp_path / "first", "team/First")
    second = git_source(tmp_path / "second", "team/Second")
    with TestClient(create_app(services[0])) as client:
        preview = client.get(
            "/api/projects/association",
            params=[("source_roots", str(first)), ("source_roots", str(second))],
        ).json()
        assert preview["deepwiki_repo"] == "" and preview["status"] == "unknown"
        created = client.post(
            "/api/projects",
            json={
                "name": "主目录优先",
                "source_root": str(first),
                "source_folders": [{"root": str(second)}],
            },
        ).json()
        assert created["deepwiki_repo"] == "team/First"
        manual = client.patch(
            f"/api/projects/{created['id']}",
            json={
                "deepwiki_repo": "https://github.com/docs/Architecture.git",
                "auto_associate": False,
            },
        )
        assert manual.status_code == 200 and manual.json()["deepwiki_repo"] == "docs/Architecture"
        rebound = client.patch(f"/api/projects/{created['id']}", json={"auto_associate": True})
        assert rebound.status_code == 200 and rebound.json()["deepwiki_repo"] == "team/First"


async def test_runs_use_each_projects_source_and_repository_without_changing_global_settings(
    services, tmp_path
):
    settings = services[-1]
    settings.save(AppSettings(deepwiki_repo="global/Original"))
    base = create_services(services[0])
    projects = Projects(base)
    projects.initialize()
    captured = {}
    try:
        for name in ("A", "B"):
            root = git_source(tmp_path / name, f"team/{name}")
            project = projects.create(ProjectCreate(name=name, source_root=str(root)))
            scoped = projects.services(project["id"])

            async def execute(run, _emit, current=scoped, label=name):
                captured[label] = (
                    current.runtime.workspace.root,
                    current_configuration(current.settings).deepwiki_repo,
                    current.runtime.workspace.read("Program.cs")["content"],
                )
                return "已读取当前项目"

            scoped.runtime.execute = execute
            run = scoped.repository.create_run(None, "读取当前项目", [])
            scoped.runs.start(run)
        await asyncio.gather(
            *(
                task
                for service in projects.contexts.values()
                for task in service.runs.tasks.values()
            )
        )
        for name in ("A", "B"):
            assert captured[name][0] == Path(tmp_path / name)
            assert captured[name][1] == f"team/{name}" and f"team/{name}" in captured[name][2]
        assert base.settings.load().deepwiki_repo == "global/Original"
    finally:
        await projects.shutdown()
        base.database.close()


async def test_deepwiki_call_cannot_query_another_projects_repository(monkeypatch):
    calls = []

    class Client:
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return SimpleNamespace(model_dump=lambda **_: {"content": []})

    @asynccontextmanager
    async def connected(_server):
        yield Client()

    monkeypatch.setattr("app.mcp_client.connect", connected)
    remote = Tool(
        name="read_wiki_structure",
        inputSchema={"type": "object", "properties": {"repoName": {"type": "string"}}},
    )
    adapter = adapt_tool(
        McpSettings(id="wiki", name="DeepWiki", url="https://example.com/mcp"),
        remote,
        repo="team/Current",
    )
    rejected = await adapter.ainvoke({"repoName": "team/Other"})
    assert "当前项目关联" in rejected and calls == []
    await adapter.ainvoke({"repoName": "TEAM/current"})
    assert calls == [("read_wiki_structure", {"repoName": "team/Current"})]


async def test_unassociated_project_does_not_connect_deepwiki(services, monkeypatch):
    from app.runtime import AgentRuntime
    from tests.test_compaction import DeterministicModel

    paths, _, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(
            mcp_servers=[McpSettings(id="wiki", name="DeepWiki", url="https://example.com/mcp")]
        )
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)

    async def forbidden(*_args):
        raise AssertionError("未关联仓库时不能借用全局 DeepWiki")

    monkeypatch.setattr(runtime, "remote_tools", forbidden)
    monkeypatch.setattr("app.runtime.create_model", lambda *_args, **_kwargs: DeterministicModel())
    monkeypatch.setattr("app.runtime.create_deep_agent", lambda **kwargs: kwargs)
    graph = await runtime.graph("unassociated", None, lambda *_: None)
    assert "DeepWiki 仓库：未配置" in graph["system_prompt"]
    assert not any(tool.name.startswith("mcp_") for tool in graph["tools"])
