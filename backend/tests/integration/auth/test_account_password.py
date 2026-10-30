import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.modules.auth.models import Account
from app.modules.auth.service import COOKIE_NAME
from tests.helpers.accounts import sign_in

pytestmark = pytest.mark.authentication


@pytest.mark.parametrize("username", ["admin", "user"])
def test_password_change_replaces_hash_and_revokes_only_own_sessions(services, username):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, username)
        auth = client.app.state.auth
        credentials = json.loads(auth.initial_accounts.read_text(encoding="utf-8"))
        old_password = next(row["password"] for row in credentials if row["username"] == username)
        old_token = client.cookies[COOKIE_NAME]
        another_token, _ = auth.authenticate(username, old_password, "another-own-window")
        other_account = next(row for row in credentials if row["username"] != username)
        unrelated_token, _ = auth.authenticate(
            other_account["username"], other_account["password"], "unrelated-window"
        )
        response = client.post(
            "/api/auth/password",
            json={
                "current_password": old_password,
                "new_password": "123456",
                "confirm_password": "123456",
            },
        )
        assert response.status_code == 204, response.text
        assert "max-age=0" in response.headers["set-cookie"].lower()
        assert auth.resolve(old_token) is None
        assert auth.resolve(another_token) is None
        assert auth.resolve(unrelated_token)["user"]["username"] == other_account["username"]
        assert client.get("/api/auth/session").status_code == 401
        assert (
            client.post(
                "/api/auth/login", json={"username": username, "password": old_password}
            ).status_code
            == 401
        )
        signed = client.post("/api/auth/login", json={"username": username, "password": "123456"})
        assert signed.status_code == 200
        assert signed.json()["user"]["role"] == username
        with auth.database.session() as session:
            account = session.scalar(select(Account).where(Account.username == username))
            assert account.password_hash.startswith("$argon2id$")
            assert auth.hasher.verify(account.password_hash, "123456")
        # 自助改密不把新密码写回初始账号文件。
        assert json.loads(auth.initial_accounts.read_text(encoding="utf-8")) == credentials


def test_password_change_rejects_invalid_old_password_confirmation_csrf_and_account_injection(
    services,
):
    with TestClient(create_app(services[0])) as client:
        body = {"current_password": "wrong", "new_password": "654321", "confirm_password": "654321"}
        assert client.post("/api/auth/password", json=body).status_code == 401
        sign_in(client, "user")
        auth = client.app.state.auth
        with auth.database.session() as session:
            account = session.scalar(select(Account).where(Account.username == "user"))
            before = account.password_hash
        assert client.post("/api/auth/password", json=body).status_code == 400
        assert (
            client.post(
                "/api/auth/password", json={**body, "confirm_password": "not-the-same"}
            ).status_code
            == 400
        )
        assert (
            client.post("/api/auth/password", json={**body, "new_password": "short"}).status_code
            == 422
        )
        assert (
            client.post("/api/auth/password", json={**body, "username": "admin"}).status_code == 422
        )
        assert (
            client.post(
                "/api/auth/password", json=body, headers={"X-Arks-CSRF": "wrong"}
            ).status_code
            == 403
        )
        assert client.get("/api/auth/session").status_code == 200
        with auth.database.session() as session:
            account = session.scalar(select(Account).where(Account.username == "user"))
            assert account.password_hash == before
