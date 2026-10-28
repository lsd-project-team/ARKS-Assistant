"""真实文件、会话和静态响应覆盖资料直链、历史分包及公开登录依赖。"""

import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urljoin

import pytest
from fastapi.testclient import TestClient

from app import bootstrap
from app.core.config import PROJECT_ROOT
from app.modules.auth.service import COOKIE_NAME
from app.modules.auth.static_assets import StaticAssets
from tests.helpers.accounts import sign_in

pytestmark = pytest.mark.authentication


@pytest.fixture
def frontend(tmp_path, monkeypatch):
    root = tmp_path / "application"
    directory = root / "frontend/dist"
    content = {
        "index.html": b'<script src="/assets/login.js"></script>',
        "assets/login.js": b"console.log('public login')",
        "assets/workspace.js": b"PRIVATE_BUSINESS_CODE_FIXTURE",
        "assets/old-unsafe.js": b"PRIVATE_LEGACY_BUNDLE_FIXTURE",
        "assets/workspace.js.map": b"PRIVATE_SOURCE_MAP_FIXTURE",
        "archify/source.html": b"PRIVATE_SOURCE_HTML_FIXTURE",
        "engineering/manifest.json": b'{"private": "PRIVATE_MANIFEST_FIXTURE"}',
        "agent-knowledge.json": b'{"private": "PRIVATE_AGENT_KNOWLEDGE_FIXTURE"}',
    }
    for name, value in content.items():
        file = directory / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(value)
    manifest = {
        "schema_version": 1,
        "files": {
            name: hashlib.sha256(content[name]).hexdigest()
            for name in ("index.html", "assets/login.js")
        },
    }
    (directory / "public-assets.json").write_text(json.dumps(manifest), encoding="utf-8")
    # 保留真实迁移配置，迁移仍只运行在services的临时SQLite，不改动正式数据。
    backend = root / "backend"
    backend.mkdir()
    shutil.copyfile(bootstrap.PROJECT_ROOT / "backend/alembic.ini", backend / "alembic.ini")
    shutil.copytree(
        bootstrap.PROJECT_ROOT / "backend/migrations",
        backend / "migrations",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    monkeypatch.setattr(bootstrap, "PROJECT_ROOT", root)
    return directory


def test_login_resources_are_public_but_private_files_cannot_bypass_session(services, frontend):
    with TestClient(bootstrap.create_app(services[0])) as client:
        assert client.get("/").content == (frontend / "index.html").read_bytes()
        public = client.get("/assets/login.js")
        assert public.content == (frontend / "assets/login.js").read_bytes()
        assert public.headers["cache-control"].startswith("public,")
        assert client.get("/").headers["cache-control"] == "no-store"
        for path in (
            "/assets/workspace.js",
            "/assets/old-unsafe.js",
            "/assets/workspace.js.map",
            "/archify/source.html",
            "/engineering/manifest.json",
            "/agent-knowledge.json",
            "/public-assets.json",
            "/archify%2fsource.html",
            "//engineering/manifest.json",
            "/archify/source.html?download=1",
            "/assets/%2e%2e/archify/source.html",
        ):
            for method in ("GET", "HEAD"):
                response = client.request(
                    method, path, headers={"Range": "bytes=0-4", "If-None-Match": "*"}
                )
                assert response.status_code == 401, path
                assert "PRIVATE" not in response.text
                assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("username", ["admin", "user"])
def test_real_session_reads_private_files_but_logout_and_cross_site_reject_them(
    services, frontend, username
):
    with TestClient(bootstrap.create_app(services[0])) as client:
        sign_in(client, username)
        for path in (
            "assets/workspace.js",
            "assets/old-unsafe.js",
            "archify/source.html",
            "engineering/manifest.json",
        ):
            response = client.get("/" + path)
            assert response.status_code == 200
            assert response.content == (frontend / path).read_bytes()
            assert response.headers["cache-control"] == "private, no-store"
            assert "cookie" in response.headers["vary"].lower()
            assert response.headers["x-frame-options"] == "SAMEORIGIN"
            assert response.headers["cross-origin-resource-policy"] == "same-origin"
        assert (
            client.get("/assets/workspace.js", headers={"Sec-Fetch-Site": "cross-site"}).status_code
            == 403
        )
        assert (
            client.get(
                "/assets/workspace.js", headers={"X-Arks-Account": "wrong-account"}
            ).status_code
            == 401
        )
        cookie = client.cookies[COOKIE_NAME]
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/assets/workspace.js").status_code == 401
        assert (
            client.get(
                "/assets/workspace.js", headers={"Cookie": f"{COOKIE_NAME}={cookie}"}
            ).status_code
            == 401
        )
        assert client.get("/assets/login.js").status_code == 200


def test_missing_manifest_keeps_api_available_and_static_files_closed(services, frontend):
    (frontend / "public-assets.json").unlink()
    with TestClient(bootstrap.create_app(services[0])) as client:
        assert client.get("/api/health").json()["ok"] is True
        assert client.get("/").status_code == 401
        assert client.get("/assets/login.js").status_code == 401


def test_public_asset_errors_are_not_cached_as_immutable_files(services, frontend):
    with TestClient(bootstrap.create_app(services[0])) as client:
        response = client.get("/assets/login.js", headers={"Range": "bytes=999999-"})
        assert response.status_code == 416
        assert response.headers["cache-control"] == "no-store"
        (frontend / "assets/login.js").unlink()
        response = client.get("/assets/login.js")
        assert response.status_code == 404
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("fault", ["digest", "version", "private", "traversal", "json"])
def test_broken_public_manifest_cannot_silently_open_private_or_changed_files(frontend, fault):
    manifest = frontend / "public-assets.json"
    value = json.loads(manifest.read_text())
    if fault == "digest":
        (frontend / "assets/login.js").write_bytes(b"PRIVATE_TAMPERED_CONTENT")
    elif fault == "version":
        value["schema_version"] = True
    elif fault in {"private", "traversal"}:
        name = (
            "engineering/manifest.json" if fault == "private" else "assets/../archify/source.html"
        )
        value["files"][name] = "a" * 64
    manifest.write_text("not-json" if fault == "json" else json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="白名单无效"):
        StaticAssets(frontend)


def test_hardlinked_public_file_is_not_accepted(frontend, tmp_path):
    original = frontend / "assets/login.js"
    os.link(original, tmp_path / "external-alias")
    with pytest.raises(ValueError, match="白名单无效"):
        StaticAssets(frontend)
    assert original.read_bytes() == b"console.log('public login')"


def test_actual_built_login_dependencies_and_private_knowledge_require_real_session(
    services, frontend
):
    configured = os.environ.get("ARKS_TEST_FRONTEND_BUILD")
    if not configured:
        pytest.skip("需显式提供本轮output中的前端构建目录")
    built = Path(configured).resolve()
    assert built == (PROJECT_ROOT / "frontend/dist").resolve() or built.is_relative_to(
        (PROJECT_ROOT / "output").resolve()
    )
    StaticAssets(built)
    public = json.loads((built / "public-assets.json").read_text(encoding="utf-8"))["files"]
    # 只复制本轮构建的UI资产和两份资料；真实数据库、会话和静态服务仍完整运行。
    shutil.copytree(built / "assets", frontend / "assets", dirs_exist_ok=True)
    for name in [
        *public,
        "public-assets.json",
        "agent-knowledge.json",
        "archify/module-source-explorer.html",
    ]:
        destination = frontend / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built / name, destination)
    private_scripts = [
        file
        for file in (frontend / "assets").rglob("*.js")
        if file.relative_to(frontend).as_posix() not in public
    ]
    assert private_scripts and any(
        file.name.startswith("KnowledgeWorkspace-") for file in private_scripts
    )
    with TestClient(bootstrap.create_app(services[0])) as client:
        assert client.get("/").status_code == 200
        for name, digest in public.items():
            response = client.get("/" + name)
            assert response.status_code == 200, name
            assert hashlib.sha256(response.content).hexdigest() == digest
            if name.endswith(".css"):
                for url in re.findall(r"url\(['\"]?([^)'\"]+)", response.text):
                    if not url.startswith("data:"):
                        assert urljoin("/" + name, url).lstrip("/") in public
        for file in private_scripts:
            assert client.get("/" + file.relative_to(frontend).as_posix()).status_code == 401
        for url in ("/agent-knowledge.json", "/archify/module-source-explorer.html"):
            assert client.get(url).status_code == 401
        sign_in(client, "user")
        sample = next(
            file for file in private_scripts if file.name.startswith("KnowledgeWorkspace-")
        )
        assert (
            client.get("/" + sample.relative_to(frontend).as_posix()).content == sample.read_bytes()
        )
        for name in ("agent-knowledge.json", "archify/module-source-explorer.html"):
            assert client.get("/" + name).content == (built / name).read_bytes()
