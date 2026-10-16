"""共享公司源码与私人项目是独立边界，新账号不能成为没有源码的空工作区。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.modules.auth.models import Account
from app.modules.projects.models import Project
from tests.helpers.accounts import login_second, sign_in

pytestmark = pytest.mark.authentication


def default_project(client):
    listing = client.get("/api/projects").json()
    return next(row for row in listing["projects"] if row["id"] == listing["default_project_id"])


def add_second(client):
    with client.app.state.auth.database.session.begin() as session:
        session.add(
            Account(
                username="second",
                display_name="第二人",
                role="user",
                password_hash=client.app.state.auth.hasher.hash("second-pass-123456"),
            )
        )


def test_each_account_automatically_gets_same_source_and_separate_empty_project(services):
    with TestClient(create_app(services[0])) as client:
        first_user = sign_in(client, "user").json()["user"]
        first = default_project(client)
        assert first["owner_id"] == first_user["id"]
        assert first["source_root"] == str(services[0].workspace)
        source = client.get(f"/api/p/{first['id']}/file?path=Program.cs")
        assert source.status_code == 200
        add_second(client)
        second_user = login_second(client)
        second = default_project(client)
        assert second["id"] != first["id"] and second["owner_id"] == second_user["id"]
        assert second["source_root"] == first["source_root"]
        assert (
            client.get(f"/api/p/{second['id']}/file?path=Program.cs").json()["version"]
            == source.json()["version"]
        )
        assert client.get(f"/api/p/{second['id']}/threads").json() == []
        assert client.get(f"/api/p/{second['id']}/memories").json() == []
        assert client.get("/api/projects/search-threads").json() == []
        assert client.get(f"/api/p/{first['id']}/threads").status_code == 404
        assert (
            client.get(f"/api/sources/{services[2].source_id}/file?path=Program.cs").status_code
            == 200
        )
        login_second(client)
        assert default_project(client)["id"] == second["id"]
        assert len(client.get("/api/projects").json()["projects"]) == 1


def test_normal_new_projects_inherit_company_source_but_arbitrary_paths_stay_forbidden(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        for body in (
            {"name": "默认关联"},
            {"name": "空目录自动关联", "source_root": None},
            {"name": "已批准目录", "source_root": str(services[0].workspace)},
        ):
            response = client.post("/api/projects", json=body)
            assert response.status_code == 201, response.text
            project = response.json()
            assert project["source_root"] == str(services[0].workspace)
            assert client.get(f"/api/p/{project['id']}/files").json()
        for body in (
            {"name": "越界", "source_root": str(services[0].data)},
            {
                "name": "越界",
                "source_root": str(services[0].workspace),
                "source_folders": [{"root": str(services[0].data)}],
            },
        ):
            assert client.post("/api/projects", json=body).status_code == 403


def test_existing_owners_keep_project_and_private_instructions_are_not_copied(services):
    with TestClient(create_app(services[0])) as client:
        # 模拟已经明确归属的旧默认项目，不能给原账号重复创建副本。
        with client.app.state.projects.database.session.begin() as session:
            user = session.scalar(select(Account).where(Account.username == "user"))
            original = session.get(Project, services[2].id)
            original.owner_id = user.id
            original.description, original.instructions = (
                "PRIVATE-DESCRIPTION",
                "PRIVATE-INSTRUCTION",
            )
            original.deepwiki_repo = "company/ZX2200"
        sign_in(client, "user")
        assert default_project(client)["id"] == services[2].id
        assert len(client.get("/api/projects").json()["projects"]) == 1
        add_second(client)
        login_second(client)
        second = default_project(client)
        assert second["description"] == second["instructions"] == ""
        assert second["deepwiki_repo"] == "company/ZX2200"
        assert "PRIVATE-" not in client.get("/api/projects").text
        snapshot = client.app.state.projects.snapshot("independent")
        assert snapshot["deepwiki_repo"] == "company/ZX2200"
        assert "PRIVATE-" not in str(snapshot)


def test_archiving_default_is_respected_and_independent_chat_still_has_source(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        original = default_project(client)
        assert (
            client.patch(f"/api/projects/{original['id']}", json={"state": "archived"}).status_code
            == 200
        )
        sign_in(client, "user")
        assert client.get("/api/projects").json()["projects"] == []
        assert len(client.get("/api/projects?state=archived").json()["projects"]) == 1
        response = client.get("/api/p/independent/file?path=Program.cs")
        assert response.status_code == 200
        assert response.json()["source_workspace_id"] == services[2].source_id
