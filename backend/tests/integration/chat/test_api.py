import os

from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers.api_paths import project_api


def test_api_migrations_validation_and_origin(services):
    paths = services[0]
    with TestClient(create_app(paths)) as client:
        health = client.get("/api/health").json()
        assert health["workspace"] == str(paths.workspace)
        assert health["data_directory"] == str(paths.data)
        assert health["process_id"] == os.getpid()
        assert (
            client.get(project_api(client, "/file"), params={"path": "../secret"}).status_code
            == 409
        )
        assert (
            client.get("/api/settings", headers={"Origin": "https://evil.example"}).status_code
            == 403
        )
        thread = client.post(project_api(client, "/threads"), json={"title": "中文对话"}).json()
        assert (
            client.get(project_api(client, f"/threads/{thread['id']}")).json()["title"]
            == "中文对话"
        )
        invalid = {
            "content": "问题",
            "selections": [
                {
                    "path": "Program.cs",
                    "start_line": 3,
                    "end_line": 1,
                    "content": "x",
                    "version": "a" * 64,
                }
            ],
        }
        assert (
            client.post(
                project_api(client, f"/threads/{thread['id']}/runs"), json=invalid
            ).status_code
            == 422
        )
        assert client.get(project_api(client, "/runs/not-found/events")).status_code == 404
        invalid_settings = {"model": {"api_key": "SECRET-MUST-NOT-ECHO", "context_tokens": 1}}
        response = client.put("/api/settings", json={"settings": invalid_settings})
        assert response.status_code == 422
        assert "SECRET-MUST-NOT-ECHO" not in response.text


def test_retired_routes_cannot_return_project_data_or_static_html(services):
    with TestClient(create_app(services[0])) as client:
        # 使用管理员身份验证路由确实移除，避免仅因普通账号无权访问而误判通过。
        for path in ("/threads", "/files", "/memories", "/source-options", "/runs/missing"):
            for method in ("GET", "POST", "PATCH", "DELETE"):
                response = client.request(method, f"/api{path}")
                assert response.status_code == 404, (method, path, response.text)
                assert response.headers["content-type"].startswith("application/json")
        for path in (
            "/api/handover/templates/task",
            "/api/handover/templates/import",
            project_api(client, "/settings"),
            project_api(client, "/mcp/probe"),
        ):
            assert client.get(path).status_code == 404, path
            assert client.post(path).status_code == 404, path
        assert client.get(project_api(client, "/files")).status_code == 200
        assert client.get("/api/settings").status_code == 200
