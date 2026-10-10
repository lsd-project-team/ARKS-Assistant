from fastapi.testclient import TestClient

from app.main import create_app


def test_api_migrations_validation_and_origin(services):
    paths = services[0]
    with TestClient(create_app(paths)) as client:
        assert client.get("/api/health").json()["workspace"] == str(paths.workspace)
        assert client.get("/api/file", params={"path": "../secret"}).status_code == 409
        assert (
            client.get("/api/settings", headers={"Origin": "https://evil.example"}).status_code
            == 403
        )
        thread = client.post("/api/threads", json={"title": "中文对话"}).json()
        assert client.get(f"/api/threads/{thread['id']}").json()["title"] == "中文对话"
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
        assert client.post(f"/api/threads/{thread['id']}/runs", json=invalid).status_code == 422
        assert client.get("/api/runs/not-found/events").status_code == 404
        invalid_settings = {"model": {"api_key": "SECRET-MUST-NOT-ECHO", "context_tokens": 1}}
        response = client.put("/api/settings", json={"settings": invalid_settings})
        assert response.status_code == 422
        assert "SECRET-MUST-NOT-ECHO" not in response.text
