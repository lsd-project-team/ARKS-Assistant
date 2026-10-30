"""原文件上传、浏览器预览及旧资料兼容；不读取或提取新文件正文。"""

import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.modules.auth.models import Account
from app.modules.handover.application.materials import import_text
from app.modules.handover.infrastructure.parsers.documents import DocumentParser
from app.modules.handover.infrastructure.persistence.repository import HandoverStore


@pytest.fixture
def client(services, monkeypatch):
    def forbidden(*_args):
        raise AssertionError("原文件上传和预览不能调用解析器")

    monkeypatch.setattr(DocumentParser, "parse", forbidden)
    monkeypatch.setattr(DocumentParser, "snapshot", forbidden)
    app = create_app(services[0])
    with TestClient(app) as current:
        auth = app.state.auth
        with auth.database.session.begin() as session:
            session.add(
                Account(
                    username="file-user",
                    display_name="文件上传人",
                    role="user",
                    password_hash=auth.hasher.hash("test-original-files-only"),
                )
            )
        login = current.post(
            "/api/auth/login",
            json={
                "username": "file-user",
                "password": "test-original-files-only",
            },
        )
        assert login.status_code == 200
        current.headers["X-Arks-CSRF"] = login.json()["csrf_token"]
        yield current


def upload(client, filename, content, **params):
    return client.post(
        "/api/handover/sources/upload", params={"filename": filename, **params}, content=content
    )


@pytest.mark.parametrize(
    "filename,content,media_type",
    [
        ("扫描.pdf", b"%PDF-not-parsed\x00\xff", "application/pdf"),
        ("文档.docx", b"PK-not-extracted\x00", "application/octet-stream"),
        ("源码.zip", b"not-opened-as-zip", "application/octet-stream"),
        ("日志.txt", "  原始换行\r\n尾部空白  \n".encode(), "text/plain"),
        ("图片.png", b"\x89PNG\r\n\x1a\nraw-image", "image/png"),
    ],
)
def test_upload_preserves_exact_bytes_without_parsing_and_uses_login(
    client, filename, content, media_type
):
    response = upload(client, filename, content, actor="不能冒充的人", notes="不应写入的隐藏字段")
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["title"] == filename
    payload = row["payload"]
    assert payload["content"] == "" and payload["files"] == [] and payload["parse_notes"] == ""
    assert payload["notes"] == "" and payload["supersedes"] == ""
    assert payload["sha256"] == hashlib.sha256(content).hexdigest()
    original = client.get(f"/api/handover/sources/{row['id']}/original")
    assert original.status_code == 200 and original.content == content
    assert original.headers["content-type"].startswith(media_type)
    assert original.headers["content-disposition"].startswith("attachment;")
    assert original.headers["x-content-type-options"] == "nosniff"
    detail = client.get(f"/api/handover/records/{row['id']}").json()
    assert detail["created_by"] == "文件上传人"
    assert detail["original_file"] == {
        "name": filename,
        "previewable": media_type != "application/octet-stream",
    }
    listed = next(
        item for item in client.get("/api/handover").json()["records"] if item["id"] == row["id"]
    )
    assert (
        listed["created_by"] == "文件上传人" and listed["original_file"] == detail["original_file"]
    )


@pytest.mark.parametrize(
    "filename,media_type,disposition",
    [
        ("手册.pdf", "application/pdf", "inline;"),
        ("原图.jpg", "image/jpeg", "inline;"),
        ("说明.md", "text/plain", "inline;"),
        ("文档.docx", "application/octet-stream", "attachment;"),
        ("页面.html", "application/octet-stream", "attachment;"),
        ("图.svg", "application/octet-stream", "attachment;"),
    ],
)
def test_preview_only_uses_safe_browser_types_and_never_changes_bytes(
    client, filename, media_type, disposition
):
    content = b"<script>not executed</script>\r\n\x00"
    row = upload(client, filename, content).json()
    response = client.get(f"/api/handover/sources/{row['id']}/original?inline=true")
    assert response.status_code == 200 and response.content == content
    assert response.headers["content-type"].startswith(media_type)
    assert response.headers["content-disposition"].startswith(disposition)
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["cache-control"] == "no-store"


def test_upload_size_and_filename_boundaries_do_not_write_bad_files(client):
    before = client.get("/api/handover").json()
    for filename, content in [
        ("空文件.pdf", b""),
        (".", b"x"),
        ("..", b"x"),
        (" ", b"x"),
        ("超限.bin", b"x" * (32 * 1024 * 1024 + 1)),
    ]:
        assert upload(client, filename, content).status_code == 409
    assert client.get("/api/handover").json() == before
    boundary = b"x" * (32 * 1024 * 1024)
    response = upload(client, "边界.bin", boundary)
    assert response.status_code == 201
    assert client.get(f"/api/handover/sources/{response.json()['id']}/original").content == boundary
    cleaned = upload(client, r"C:\incoming\文件.txt", b"raw")
    assert cleaned.status_code == 201 and cleaned.json()["payload"]["filename"] == "文件.txt"


def test_username_fallback_and_authentication_are_enforced(client):
    auth = client.app.state.auth
    with auth.database.session.begin() as session:
        account = session.scalar(select(Account).where(Account.username == "file-user"))
        account.display_name = ""
    row = upload(client, "记录.txt", b"raw").json()
    detail = client.get(f"/api/handover/records/{row['id']}").json()
    assert detail["created_by"] == "file-user"
    client.cookies.clear()
    assert client.get(f"/api/handover/sources/{row['id']}/original?inline=true").status_code == 401
    assert upload(client, "未登录.txt", b"raw").status_code == 401


def test_existing_text_and_fixed_references_remain_available_without_new_extraction(client):
    store = HandoverStore(client.app.state.projects)
    content = "旧文本\r\n  保留空白  \n"
    old = import_text(store, "历史文件", content, {}, "原整理人")
    interview = store.create("interview", "历史访谈", {"transcript": content}, "原访谈整理人")
    for row in [old, interview]:
        before = store.get(row["id"], 1)
        original = client.get(f"/api/handover/sources/{row['id']}/original?inline=true")
        assert original.status_code == 200 and original.content == content.encode()
        assert original.headers["content-type"].startswith("text/plain")
        assert store.get(row["id"], 1) == before
    assert store.get(old["id"])["created_by"] == "原整理人"
    assert store.get(interview["id"])["original_file"] is None
    assert client.get("/api/handover/sources/missing/original?inline=true").status_code == 404


def test_original_survives_service_reopen(services):
    with TestClient(create_app(services[0])) as first:
        row = upload(first, "原始.doc", b"\x00\xffunparsed\r\n").json()
    with TestClient(create_app(services[0])) as reopened:
        original = reopened.get(f"/api/handover/sources/{row['id']}/original")
        assert original.status_code == 200 and original.content == b"\x00\xffunparsed\r\n"
        assert reopened.get(f"/api/handover/records/{row['id']}").json()["payload"]["content"] == ""
