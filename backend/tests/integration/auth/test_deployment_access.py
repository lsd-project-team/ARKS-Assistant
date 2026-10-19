"""真实临时应用、SQLite 和登录流程验证公司域名/IP部署，不调用模型。"""

import pytest
from fastapi.testclient import TestClient

from app import bootstrap
from app.bootstrap import create_app
from app.modules.auth.service import COOKIE_NAME
from tests.helpers.accounts import sign_in

pytestmark = pytest.mark.authentication


@pytest.mark.parametrize(
    "address,host",
    [("https://arks.example", "arks.example"), ("http://192.0.2.20:8765", "192.0.2.20")],
)
def test_configured_same_origin_can_login_but_mutations_still_need_csrf(
    services, monkeypatch, address, host
):
    monkeypatch.setenv("ARKS_ALLOWED_ORIGINS", address)
    monkeypatch.setenv("ARKS_TRUSTED_HOSTS", host)
    with TestClient(create_app(services[0]), base_url=address) as client:
        client.headers["Origin"] = address
        assert client.get("/api/auth/session").status_code == 401
        response = sign_in(client)
        assert response.json()["user"]["role"] == "admin"
        assert ("; secure" in response.headers["set-cookie"].lower()) == address.startswith("https")
        assert client.get("/api/auth/session").status_code == 200
        body = {"name": "公司服务器上的项目"}
        assert client.post("/api/projects", json=body).status_code == 201
        client.headers.pop("X-Arks-CSRF")
        assert client.post("/api/projects", json=body).status_code == 403


def test_proxy_transport_scheme_is_not_trusted_as_an_origin_or_host_override(services, monkeypatch):
    monkeypatch.setenv("ARKS_ALLOWED_ORIGINS", "https://arks.example")
    monkeypatch.setenv("ARKS_TRUSTED_HOSTS", "arks.example")
    # TLS可在受信代理终止；应用只使用显式Origin和原始Host，不推断任意转发头。
    with TestClient(create_app(services[0]), base_url="http://arks.example") as client:
        client.headers["Origin"] = "https://arks.example"
        login = sign_in(client)
        cookie = login.headers["set-cookie"].lower()
        assert "secure" in cookie and "samesite=strict" in cookie and "httponly" in cookie
        # 外部浏览器通过HTTPS发送Secure Cookie；内部HTTP代理仍照常转交Cookie头。
        client.headers["Cookie"] = f"{COOKIE_NAME}={client.cookies[COOKIE_NAME]}"
        listing = client.get("/api/projects")
        assert listing.status_code == 200
        original_names = {row["name"] for row in listing.json()["projects"]}
        assert client.post("/api/projects", json={"name": "代理后的项目"}).status_code == 201
        for headers in (
            {"Origin": "https://evil.example", "X-Forwarded-Host": "arks.example"},
            {"Host": "evil.example", "X-Forwarded-Host": "arks.example"},
            {"Origin": "https://arks.example", "Sec-Fetch-Site": "cross-site"},
        ):
            response = client.post("/api/projects", json={"name": "不应创建"}, headers=headers)
            assert response.status_code == 403
        names = {row["name"] for row in client.get("/api/projects").json()["projects"]}
        assert names - original_names == {"代理后的项目"}
        logout = client.post("/api/auth/logout")
        assert logout.status_code == 204
        assert "secure" in logout.headers["set-cookie"].lower()
        assert "samesite=strict" in logout.headers["set-cookie"].lower()
        assert client.get("/api/auth/session").status_code == 401


def test_invalid_deployment_configuration_fails_before_paths_or_services_are_created(monkeypatch):
    monkeypatch.setenv("ARKS_ALLOWED_ORIGINS", "https://secret@arks.example")
    monkeypatch.setenv("ARKS_TRUSTED_HOSTS", "arks.example")

    def no_paths():
        raise AssertionError("非法部署配置不应触碰正式目录")

    monkeypatch.setattr(bootstrap, "Paths", no_paths)
    with pytest.raises(ValueError) as failure:
        create_app()
    assert "secret" not in str(failure.value)
