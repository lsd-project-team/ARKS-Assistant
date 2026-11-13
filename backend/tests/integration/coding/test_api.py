"""项目编码 API：目录树、读写、命令与检查点的项目级路由。"""

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth.models import Account
from tests.helpers.accounts import login_second, sign_in


def test_project_coding_api_reads_writes_runs_and_restores(services, tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "admin")
        project = client.post(
            "/api/projects", json={"name": "编码项目", "source_root": str(root)}
        ).json()
        base = f"/api/p/{project['id']}/coding"

        response = client.put(
            base + "/settings",
            json={"approval_mode": "full", "timeout_seconds": 60},
        )
        assert response.status_code == 200, response.text

        created = client.put(
            base + "/file",
            json={"path": "docs/readme.md", "content": "# 通信协议\n"},
        )
        assert created.status_code == 200, created.text
        version = created.json()["version"]

        tree = client.get(base + "/tree").json()
        assert "docs/readme.md" in tree["entries"]

        read = client.get(base + "/file", params={"path": "docs/readme.md"}).json()
        assert "通信协议" in read["content"] and read["version"] == version

        command = client.post(
            base + "/command",
            json={"command": "Get-Content docs/readme.md", "approved": True},
        ).json()
        assert command["exit_code"] == 0
        assert "通信协议" in command["output"]

        points = client.get(base + "/checkpoints").json()
        assert points["checkpoints"]

        # 旧副本与合并接口已经移除，不能再注册或误用。
        assert client.get("/api/settings/code-work").status_code == 404
        assert client.get(base.replace("/coding", "/threads/x/code-work")).status_code in {404, 405}

        result = root / "docs/readme.md"
        assert result.is_file()
        assert "通信协议" in result.read_text(encoding="utf-8")


def test_project_coding_api_edits_binary_approves_and_audits(services, tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "admin")
        project = client.post(
            "/api/projects", json={"name": "编码编辑", "source_root": str(root)}
        ).json()
        base = f"/api/p/{project['id']}/coding"
        client.put(base + "/settings", json={"approval_mode": "full", "timeout_seconds": 60})

        created = client.put(
            base + "/file", json={"path": "src/main.py", "content": "def run():\n    return 1\n"}
        ).json()
        edited = client.patch(
            base + "/file",
            json={
                "path": "src/main.py",
                "edits": [{"old": "return 1", "new": "return 2"}],
                "expected_hash": created["version"],
            },
        )
        assert edited.status_code == 200, edited.text
        assert "return 2" in (root / "src/main.py").read_text(encoding="utf-8")

        binary = client.put(
            base + "/binary",
            json={"path": "assets/icon.png", "content_base64": "iVBORw0KGgo="},
        )
        assert binary.status_code == 200, binary.text
        assert (root / "assets/icon.png").read_bytes() == b"\x89PNG\r\n\x1a\n"

        client.put(base + "/settings", json={"approval_mode": "allowlist"})
        pending = client.post(base + "/command", json={"command": "Get-Location"}).json()
        assert pending["approval_required"]
        approval_id = pending["approval"]["id"]
        assert client.get(base + "/approvals").json()["approvals"][0]["id"] == approval_id

        decided = client.post(base + f"/approvals/{approval_id}", json={"approved": True}).json()
        assert decided["status"] == "approved"
        assert decided["result"]["exit_code"] == 0

        audit = client.get(base + "/audit").json()["rows"]
        assert audit and audit[0]["command"]


def test_permission_switch_requires_admin_and_scope_applies(services, tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    app = create_app(services[0])
    with TestClient(app) as client:
        with app.state.auth.database.session.begin() as session:
            session.add(
                Account(
                    username="second",
                    display_name="第二人",
                    role="user",
                    password_hash=app.state.auth.hasher.hash("second-pass-123456"),
                )
            )
        sign_in(client, "admin")
        project = client.post(
            "/api/projects", json={"name": "权限项目", "source_root": str(root)}
        ).json()
        base = f"/api/p/{project['id']}/coding"

        switched = client.put(base + "/settings", json={"permission": "read-only"}).json()
        assert switched["permission"] == "read-only"
        assert switched["writable"] is False
        blocked = client.put(base + "/file", json={"path": "note.txt", "content": "x"})
        assert blocked.status_code == 409
        assert "仅可查看" in blocked.json()["detail"]

        # 普通成员不能给自己提权。
        login_second(client)
        own = client.post(
            "/api/projects", json={"name": "乙的项目", "source_root": str(other)}
        ).json()
        denied = client.put(
            f"/api/p/{own['id']}/coding/settings", json={"permission": "full-access"}
        )
        assert denied.status_code == 403

        sign_in(client, "admin")
        client.put(base + "/settings", json={"permission": "workspace-write"})
        pending = client.post(base + "/command", json={"command": "Get-Location"}).json()
        assert pending["approval_required"]
        decided = client.post(
            base + f"/approvals/{pending['approval']['id']}",
            json={"approved": True, "scope": "session"},
        ).json()
        assert decided["status"] == "approved"
        # 面板直接发起的命令没有对话线程，只能按一次性授权处理。
        assert decided["scope"] == "once"

        again = client.post(base + "/command", json={"command": "Get-Location"}).json()
        assert again["approval_required"]

        invalid = client.post(
            base + f"/approvals/{again['approval']['id']}",
            json={"approved": True, "scope": "always"},
        )
        assert invalid.status_code == 422
