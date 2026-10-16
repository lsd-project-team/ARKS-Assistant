"""通过真实登录、项目路由和SQLite检查补齐验收入口，拒绝过期/跨项目写入。"""

from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers.accounts import sign_in


def payload(change, **updates):
    fields = (
        "title",
        "goal",
        "acceptance_criteria",
        "constraints",
        "allowed_paths",
        "change_version",
        "requirements_version",
    )
    return {**{key: change[key] for key in fields}, **updates}


def test_contract_api_fills_old_copy_and_enforces_identity_ownership_and_archive(services):
    paths = services[0]
    original = (paths.workspace / "Program.cs").read_bytes()
    with TestClient(create_app(paths)) as client:
        project = client.post(
            "/api/projects", json={"name": "补齐验收", "source_root": str(paths.workspace)}
        ).json()
        url = f"/api/p/{project['id']}/code-changes"
        change = client.post(url, json={"title": "入口", "goal": "保持入口可用"}).json()
        updated = client.put(
            f"{url}/{change['id']}/requirements",
            json=payload(change, acceptance_criteria=["入口仍可读"], allowed_paths=["Program.cs"]),
        )
        assert updated.status_code == 200, updated.text
        saved = updated.json()
        assert saved["acceptance_criteria"] == ["入口仍可读"]
        assert saved["requirements_version"] != change["requirements_version"]
        old_file = client.get(f"{url}/{change['id']}/file", params={"path": "Program.cs"}).json()
        next_contract = client.put(
            f"{url}/{change['id']}/requirements", json=payload(saved, constraints="新限制")
        ).json()
        stale_edit = client.patch(
            f"{url}/{change['id']}/file",
            json={
                "path": old_file["path"],
                "before": old_file["content"],
                "after": "不能保存",
                "version": old_file["version"],
                "requirements_version": old_file["requirements_version"],
            },
        )
        assert stale_edit.status_code == 409 and "需求约定已变化" in stale_edit.text
        saved = next_contract
        assert (
            client.put(f"{url}/{change['id']}/requirements", json=payload(change)).status_code
            == 409
        )
        assert (
            client.put(
                f"{url}/{change['id']}/requirements",
                json=payload(saved, allowed_paths=["../secret"]),
            ).status_code
            == 422
        )
        sign_in(client, "user")
        assert (
            client.put(f"{url}/{change['id']}/requirements", json=payload(saved)).status_code == 404
        )
        sign_in(client, "admin")
        assert (
            client.patch(f"/api/projects/{project['id']}", json={"state": "archived"}).status_code
            == 200
        )
        assert (
            client.put(
                f"{url}/{change['id']}/requirements", json=payload(saved, goal="不能写归档项目")
            ).status_code
            == 409
        )
    assert (paths.workspace / "Program.cs").read_bytes() == original
