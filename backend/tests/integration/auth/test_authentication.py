import io
import json
from datetime import UTC, datetime, timedelta
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.modules.auth.models import Account, LoginSession
from app.modules.auth.service import COOKIE_NAME, token_hash
from tests.helpers.accounts import sign_in

pytestmark = pytest.mark.authentication


def source_and_package(client):
    source = client.post(
        "/api/handover/sources/text",
        json={
            "title": "授权资料",
            "content": "普通用户可查看的资料正文",
            "actor": "整理人",
        },
    ).json()
    confirmed = client.post(
        f"/api/handover/records/{source['id']}/confirm",
        json={
            "version": source["version"],
            "actor": "管理员",
            "role": "复核人",
            "opinion": "PRIVATE-REVIEW-OPINION",
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    package = client.post(
        "/api/handover/packages",
        json={
            "title": "固定版本包",
            "record_ids": [source["id"]],
            "actor": "整理人",
        },
    )
    assert package.status_code == 201, package.text
    return confirmed.json(), package.json()


def test_unauthenticated_api_and_valid_login_cookie(services):
    with TestClient(create_app(services[0])) as client:
        assert client.get("/api/health").status_code == 200
        for path in (
            "/api/auth/session",
            "/api/projects",
            "/api/handover",
            "/api/handover/events",
            "/api/settings",
            "/api/p/independent/threads",
        ):
            assert client.get(path).status_code == 401
        response = sign_in(client)
        body = response.json()
        assert body["user"]["role"] == "admin"
        assert "password" not in body["user"] and "password_hash" not in body["user"]
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=strict" in cookie
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/auth/session").json() == body
        with client.app.state.auth.database.session() as session:
            account = session.scalar(select(Account).where(Account.username == "admin"))
            assert account.password_hash.startswith("$argon2id$")
            token = client.cookies[COOKIE_NAME]
            assert session.get(LoginSession, token) is None
            assert session.get(LoginSession, token_hash(token)) is not None


def test_https_cookie_and_mutation_csrf(services):
    with TestClient(create_app(services[0]), base_url="https://testserver") as client:
        assert "secure" in sign_in(client).headers["set-cookie"].lower()
        body = {"name": "已登录项目"}
        assert client.post("/api/projects", json=body).status_code == 201
        assert (
            client.post("/api/projects", json=body, headers={"X-Arks-CSRF": "wrong"}).status_code
            == 403
        )
        client.headers.pop("X-Arks-CSRF")
        assert client.post("/api/projects", json=body).status_code == 403


def test_invalid_login_role_injection_cross_site_and_rate_limit(services):
    with TestClient(create_app(services[0])) as client:
        response = sign_in(client, "user")
        assert response.json()["user"]["role"] == "user"
        assert client.get("/api/handover/events", headers={"X-Role": "admin"}).status_code == 403
        assert (
            client.post(
                "/api/auth/login", json={"username": "user", "password": "wrong", "role": "admin"}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "wrong"},
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "wrong"},
                headers={"Sec-Fetch-Site": "cross-site"},
            ).status_code
            == 403
        )
        messages = []
        for index in range(10):
            failed = client.post(
                "/api/auth/login",
                json={"username": "admin" if index % 2 else "missing", "password": "wrong"},
            )
            assert failed.status_code == 401
            messages.append(failed.json())
        assert all(message == messages[0] for message in messages)
        assert (
            client.post(
                "/api/auth/login", json={"username": "admin", "password": "wrong"}
            ).status_code
            == 429
        )


def test_user_cannot_read_or_modify_review_but_business_operations_remain(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client)
        source, package = source_and_package(client)
        assert client.get("/api/handover/events").status_code == 200
        assert client.get(f"/api/handover/records/{source['id']}/history").status_code == 200
        assert (
            client.get(f"/api/handover/records/{source['id']}").json()["confirmation"]["opinion"]
            == "PRIVATE-REVIEW-OPINION"
        )
        sign_in(client, "user")
        for path in ("/api/handover", "/api/handover/context", "/api/handover/schema"):
            assert client.get(path).status_code == 200
        assert client.get("/api/handover/events").status_code == 403
        assert client.get(f"/api/handover/records/{source['id']}/history").status_code == 403
        body = {
            "version": source["version"],
            "actor": "管理员",
            "role": "管理员",
            "opinion": "冒名复核",
        }
        for action in ("confirm", "reject"):
            assert (
                client.post(f"/api/handover/records/{source['id']}/{action}", json=body).status_code
                == 403
            )
        assert (
            client.post(
                "/api/handover/candidates/not-found/promote",
                json={**body, "title": "候选", "proposed": {}},
            ).status_code
            == 403
        )
        assert client.post("/api/backup").status_code == 403
        for suffix in ("", "?version=1", f"?version={source['version']}"):
            result = client.get(f"/api/handover/records/{source['id']}{suffix}")
            assert result.status_code == 200
            assert "confirmation" not in result.json()
            assert "PRIVATE-REVIEW-OPINION" not in result.text
        task = client.post(
            "/api/handover/records",
            json={
                "kind": "task",
                "title": "普通用户任务",
                "payload": {"goal": "正常工作", "owner": "普通用户"},
                "actor": "普通用户",
            },
        )
        assert task.status_code == 201
        changed = client.patch(
            f"/api/handover/records/{task.json()['id']}",
            json={
                "kind": "task",
                "title": "普通用户任务",
                "payload": {"goal": "正常工作", "owner": "普通用户", "work_status": "doing"},
                "actor": "普通用户",
                "version": 1,
            },
        )
        assert changed.status_code == 200
        response = client.get(f"/api/handover/packages/{package['id']}/export?format=zip")
        assert response.status_code == 200
        with ZipFile(io.BytesIO(response.content)) as bundle:
            manifest = json.loads(bundle.read("manifest.json"))
            assert "confirmation" not in manifest["records"][0]
            assert "PRIVATE-REVIEW-OPINION" not in bundle.read("manifest.json").decode()
            with ZipFile(io.BytesIO(bundle.read("handover.docx"))) as document:
                assert b"PRIVATE-REVIEW-OPINION" not in document.read("word/document.xml")


def test_account_switch_logout_expiry_disable_and_live_role_change(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client)
        old = client.cookies[COOKIE_NAME]
        sign_in(client, "user")
        assert client.app.state.auth.resolve(old) is None
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/auth/session").status_code == 401
        sign_in(client)
        auth = client.app.state.auth
        with auth.database.session.begin() as session:
            account = session.scalar(select(Account).where(Account.username == "admin"))
            account.role = "user"
        assert client.get("/api/auth/session").json()["user"]["role"] == "user"
        assert client.get("/api/handover/events").status_code == 403
        with auth.database.session.begin() as session:
            account = session.scalar(select(Account).where(Account.username == "admin"))
            account.enabled = False
        assert client.get("/api/auth/session").status_code == 401
        sign_in(client, "user")
        with auth.database.session.begin() as session:
            session.get(LoginSession, token_hash(client.cookies[COOKIE_NAME])).expires_at = (
                datetime.now(UTC) - timedelta(seconds=1)
            ).isoformat()
        assert client.get("/api/auth/session").status_code == 401


def test_restart_preserves_accounts_but_revokes_old_sessions_and_plaintext_is_not_backed_up(
    services,
):
    paths = services[0]
    with TestClient(create_app(paths)) as first:
        sign_in(first)
        old = first.cookies[COOKIE_NAME]
        backup = first.post("/api/backup")
        assert backup.status_code == 200
        with ZipFile(io.BytesIO(backup.content)) as bundle:
            assert not any("initial-accounts" in name for name in bundle.namelist())
    with TestClient(create_app(paths)) as second:
        second.cookies.set(COOKIE_NAME, old)
        assert second.get("/api/auth/session").status_code == 401
        assert sign_in(second).status_code == 200


def test_user_cannot_turn_source_or_mcp_configuration_into_an_admin_password_read(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        project = client.post("/api/projects", json={"name": "用户的源码项目"}).json()
        sign_in(client)
        assert (
            client.patch(
                f"/api/projects/{project['id']}", json={"source_root": str(services[0].workspace)}
            ).status_code
            == 200
        )
        sign_in(client, "user")
        assert client.get("/api/settings").status_code == 200
        for url, expected in (("/api/settings", 403), (f"/api/p/{project['id']}/settings", 404)):
            assert (
                client.put(
                    url,
                    json={
                        "settings": {
                            "mcp_servers": [
                                {"id": "local", "transport": "stdio", "command": "powershell"}
                            ]
                        }
                    },
                ).status_code
                == expected
            )
        assert (
            client.post(
                "/api/mcp/local/probe",
                json={"server": {"id": "local", "transport": "stdio", "command": "powershell"}},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/projects", json={"name": "非法目录", "source_root": str(services[0].data)}
            ).status_code
            == 403
        )
        for body in (
            {"source_root": str(services[0].data)},
            {"source_folders": [{"root": str(services[0].data)}]},
        ):
            assert client.patch(f"/api/projects/{project['id']}", json=body).status_code == 403
        assert (
            client.patch(
                f"/api/projects/{project['id']}", json={"name": "只改项目名称"}
            ).status_code
            == 200
        )
        assert client.post("/api/projects", json={"name": "普通用户新项目"}).status_code == 201
