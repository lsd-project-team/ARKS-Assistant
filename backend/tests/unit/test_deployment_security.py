"""显式部署边界只认管理员声明；不借用代理头、模糊域名或 URL 容错。"""

import pytest
from starlette.datastructures import Headers

from app.core.deployment_security import DeploymentSecurity


def configured(monkeypatch, origins="https://arks.example", hosts="arks.example"):
    monkeypatch.setenv("ARKS_ALLOWED_ORIGINS", origins)
    monkeypatch.setenv("ARKS_TRUSTED_HOSTS", hosts)
    return DeploymentSecurity.from_environment()


@pytest.mark.parametrize(
    "origins,hosts",
    [
        ("", "arks.example"),
        ("https://arks.example", ""),
        ("https://arks.example,", "arks.example"),
        ("https://arks.example", "arks.example,"),
        ("*", "arks.example"),
        ("https://*.example", "arks.example"),
        ("https://arks.example", "*.example"),
        ("ftp://arks.example", "arks.example"),
        ("https://user:password@arks.example", "arks.example"),
        ("https://arks.example/path", "arks.example"),
        ("https://arks.example?secret", "arks.example"),
        ("https://arks.example?", "arks.example"),
        ("https://arks.example#fragment", "arks.example"),
        ("https://arks.example#", "arks.example"),
        ("https://arks.example:0", "arks.example"),
        ("https://arks.example:65536", "arks.example"),
        ("https://arks.example:secret", "arks.example"),
        ("https://[secret]", "arks.example"),
        ("https://arks.example", "other.example"),
        ("https://arks.example", "https://arks.example"),
        ("https://arks.example", "arks.example:443"),
        ("https://arks.example", "arks.example/path"),
        ("https://arks.example", "arks.example.."),
        ("http://[::1]evil.example", "::1"),
        ("http://[::1%*]", "::1%*"),
        ("http://[::1%eth0]", "::1%eth0"),
        ("http://127.1", "127.1"),
        ("null", "arks.example"),
    ],
)
def test_invalid_or_ambiguous_deployment_configuration_is_rejected(monkeypatch, origins, hosts):
    with pytest.raises(ValueError) as failure:
        configured(monkeypatch, origins, hosts)
    assert "password" not in str(failure.value)
    assert "secret" not in str(failure.value)


@pytest.mark.parametrize("missing", ["ARKS_ALLOWED_ORIGINS", "ARKS_TRUSTED_HOSTS"])
def test_both_environment_fields_are_required(monkeypatch, missing):
    configured(monkeypatch)
    monkeypatch.delenv(missing)
    with pytest.raises(ValueError, match="同时配置"):
        DeploymentSecurity.from_environment()


def test_exact_origin_canonicalization_and_ipv6(monkeypatch):
    policy = configured(
        monkeypatch,
        "https://ARKS.example:443/,http://192.0.2.20:8765,http://[fd00:0::1]:8765",
        "arks.example,192.0.2.20,[fd00::1]",
    )
    assert policy.allowed_origins == {
        "https://arks.example",
        "http://192.0.2.20:8765",
        "http://[fd00::1]:8765",
    }
    assert not policy.rejection(Headers({"Host": "ARKS.EXAMPLE", "Origin": "https://arks.example"}))
    assert not policy.rejection(
        Headers({"Host": "[fd00::1]:8765", "Origin": "http://[fd00::1]:8765"})
    )


@pytest.mark.parametrize(
    "host,origin",
    [
        ("evil.example", "https://arks.example"),
        ("arks.example.evil", "https://arks.example"),
        ("arks.example@evil.example", "https://arks.example"),
        ("arks.example:invalid", "https://arks.example"),
        ("arks.example", "http://arks.example"),
        ("arks.example", "https://arks.example:444"),
        ("arks.example", "https://user@arks.example"),
        ("arks.example", "https://arks.example/path"),
        ("arks.example", "https://arks.example.evil"),
        ("arks.example", "null"),
        ("[::1]arks.example", "https://arks.example"),
        ("arks.example", "http://[::1]arks.example"),
    ],
)
def test_request_host_and_origin_are_both_checked(monkeypatch, host, origin):
    policy = configured(monkeypatch)
    assert policy.rejection(
        Headers({"Host": host, "Origin": origin, "X-Forwarded-Host": "arks.example"})
    )


@pytest.mark.parametrize("field", [b"host", b"origin"])
def test_duplicate_security_headers_are_rejected(monkeypatch, field):
    policy = configured(monkeypatch)
    value = b"arks.example" if field == b"host" else b"https://arks.example"
    headers = [(b"host", b"arks.example"), (b"origin", b"https://arks.example"), (field, value)]
    assert policy.rejection(Headers(raw=headers))


def test_unconfigured_mode_keeps_local_browser_ports_without_opening_external_origins(monkeypatch):
    monkeypatch.delenv("ARKS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("ARKS_TRUSTED_HOSTS", raising=False)
    policy = DeploymentSecurity.from_environment()
    assert not policy.rejection(Headers({"Host": "testserver"}))
    assert not policy.rejection(
        Headers({"Host": "localhost:8765", "Origin": "http://localhost:5173"})
    )
    assert not policy.rejection(Headers({"Host": "[::1]:8765", "Origin": "http://[::1]:5173"}))
    assert policy.rejection(Headers({"Host": "localhost", "Origin": "https://arks.example"}))


def test_cookie_transport_uses_declared_https_boundary_without_proxy_header_guessing(monkeypatch):
    policy = configured(monkeypatch)
    assert policy.secure_cookie("http")
    assert policy.secure_cookie("https")
    mixed = configured(
        monkeypatch, "https://arks.example,http://localhost:8765", "arks.example,localhost"
    )
    assert mixed.secure_cookie("http", "https://arks.example")
    assert not mixed.secure_cookie("http", "http://localhost:8765")
    assert not mixed.secure_cookie("http", "https://evil.example")
    assert not DeploymentSecurity().secure_cookie("http")
    assert DeploymentSecurity().secure_cookie("https")
