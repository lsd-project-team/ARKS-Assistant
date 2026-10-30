"""仅对隔离测试应用使用真实登录流程。"""

import json


def sign_in(client, username="admin"):
    credentials = json.loads(client.app.state.auth.initial_accounts.read_text(encoding="utf-8"))
    account = next(item for item in credentials if item["username"] == username)
    response = client.post(
        "/api/auth/login", json={"username": username, "password": account["password"]}
    )
    assert response.status_code == 200, response.text
    client.headers["X-Arks-CSRF"] = response.json()["csrf_token"]
    return response


def login_second(client):
    response = client.post(
        "/api/auth/login", json={"username": "second", "password": "second-pass-123456"}
    )
    assert response.status_code == 200
    client.headers["X-Arks-CSRF"] = response.json()["csrf_token"]
    return response.json()["user"]
