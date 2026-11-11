"""工作区 API：管理员配置、文件读写、差异与还原。"""

from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers.api_paths import project_api


def test_workspace_api_roundtrip(services, tmp_path):
    area = tmp_path / "workspace"
    area.mkdir()
    target = area / "hello.cs"
    target.write_text("class Hello { int Value = 1; }\n", encoding="utf-8")
    with TestClient(create_app(services[0])) as client:
        base = project_api(client, "")
        config = client.get(base + "/workspace-work")
        assert config.status_code == 200 and config.json()["root"] == ""
        body = {key: value for key, value in config.json().items() if key != "windows"}
        body["root"] = str(area)
        saved = client.put(base + "/workspace-work", json=body)
        assert saved.status_code == 200, saved.text
        assert saved.json()["root"].endswith("workspace")

        thread = client.post(base + "/threads", json={}).json()
        prefix = base + f"/threads/{thread['id']}/workspace-work"
        status = client.get(prefix).json()
        assert status["exists"] and status["configured"]

        read = client.get(prefix + "/file", params={"path": "hello.cs"}).json()
        assert read["content"].startswith("1: class Hello")
        write = client.put(
            prefix + "/file",
            json={
                "path": "hello.cs",
                "version": read["version"],
                "content": "class Hello { int Value = 2; }\n",
            },
        )
        assert write.status_code == 200 and write.json()["changed"]
        assert target.read_text(encoding="utf-8").startswith("class Hello { int Value = 2")

        diff = client.get(prefix + "/diff", params={"path": "hello.cs"}).json()
        assert diff["additions"] == 1 and diff["deletions"] == 1
        summary = client.get(prefix).json()
        assert summary["additions"] == 1

        restored = client.post(prefix + "/restore", json={"path": "hello.cs"})
        assert restored.status_code == 200
        assert target.read_text(encoding="utf-8").startswith("class Hello { int Value = 1")
        assert client.get(prefix).json()["file_count"] == 0


def test_workspace_config_rejects_data_directory_and_requires_admin(services):
    with TestClient(create_app(services[0])) as client:
        base = project_api(client, "")
        config = client.get(base + "/workspace-work").json()
        body = {key: value for key, value in config.items() if key != "windows"}
        body["root"] = str(services[0].data)
        rejected = client.put(base + "/workspace-work", json=body)
        assert rejected.status_code in {403, 409, 422}
        assert rejected.status_code != 200
