"""项目编码 API：目录树、读写、命令与检查点的项目级路由。"""

from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers.accounts import sign_in


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

        result = root / "docs/readme.md"
        assert result.is_file()
        assert "通信协议" in result.read_text(encoding="utf-8")
