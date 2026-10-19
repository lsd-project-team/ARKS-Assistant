"""源码身份与项目身份分开，独立对话使用公司默认源码但不继承私人项目内容。"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth.models import Account
from app.modules.source_analysis.workspace import Workspace
from tests.helpers.accounts import login_second, sign_in

pytestmark = pytest.mark.authentication


def test_independent_and_same_source_project_have_identical_source_capabilities(services):
    with TestClient(create_app(services[0])) as client:
        assert client.get("/api/projects/independent/source-context").status_code == 401
        sign_in(client, "user")
        project = client.get("/api/projects").json()["projects"][0]
        assert (
            client.patch(
                f"/api/projects/{project['id']}",
                json={"instructions": "PRIVATE-INSTRUCTION", "description": "PRIVATE-DESCRIPTION"},
            ).status_code
            == 200
        )
        independent = client.get("/api/projects/independent/source-context")
        scoped = client.get(f"/api/projects/{project['id']}/source-context")
        assert independent.status_code == scoped.status_code == 200
        assert independent.json() == {
            "scope_id": "independent",
            "source_workspace_id": services[2].source_id,
            "attached_source_ids": [],
            "knowledge_available": True,
        }
        assert {k: v for k, v in independent.json().items() if k != "scope_id"} == {
            k: v for k, v in scoped.json().items() if k != "scope_id"
        }
        assert "PRIVATE-" not in independent.text
        assert (
            client.get("/api/p/independent/file?path=Program.cs").json()["source_workspace_id"]
            == independent.json()["source_workspace_id"]
        )


def test_context_uses_actual_changed_source_and_attached_ids(services, tmp_path):
    primary, attached = tmp_path / "other", tmp_path / "library"
    primary.mkdir()
    attached.mkdir()
    with TestClient(create_app(services[0])) as client:
        sign_in(client)
        project = client.post(
            "/api/projects",
            json={"name": "切换目录", "source_root": str(services[0].workspace)},
        ).json()
        first = client.get(f"/api/projects/{project['id']}/source-context").json()
        assert first["knowledge_available"] is True
        response = client.patch(
            f"/api/projects/{project['id']}",
            json={"source_root": str(primary), "source_folders": [{"root": str(attached)}]},
        )
        assert response.status_code == 200, response.text
        changed = client.get(f"/api/projects/{project['id']}/source-context").json()
        assert changed == {
            "scope_id": project["id"],
            "source_workspace_id": Workspace(primary).source_id,
            "attached_source_ids": [Workspace(attached).source_id],
            "knowledge_available": False,
        }
        assert client.get("/api/projects/independent/source-context").json() == {
            **first,
            "scope_id": "independent",
        }


def test_source_context_does_not_bypass_project_owner_or_expose_deleted_project(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        project = client.get("/api/projects").json()["projects"][0]
        with client.app.state.auth.database.session.begin() as session:
            session.add(
                Account(
                    username="second",
                    display_name="第二人",
                    role="user",
                    password_hash=client.app.state.auth.hasher.hash("second-pass-123456"),
                )
            )
        login_second(client)
        assert client.get(f"/api/projects/{project['id']}/source-context").status_code == 404
        assert client.get("/api/projects/not-found/source-context").status_code == 404
        assert client.get("/api/projects/independent/source-context").status_code == 200
        sign_in(client, "user")
        assert client.delete(f"/api/projects/{project['id']}").status_code == 200
        assert client.get(f"/api/projects/{project['id']}/source-context").status_code == 404
        assert client.get("/api/projects/independent/source-context").json()["knowledge_available"]
