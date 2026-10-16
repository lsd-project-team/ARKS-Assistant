"""资料详情只补充真实上传信息，不把审核身份混入整理人。"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(services):
    with TestClient(create_app(services[0])) as value:
        yield value


def add_source(client, actor="上传整理人", **changes):
    response = client.post(
        "/api/handover/sources/text",
        json={
            "title": "资料详情验证",
            "actor": actor,
            "content": "  原文\r\n\r\n保留换行与尾部空白  \n",
            "notes": "用户填写的来源说明",
            **changes,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_source_organizer_is_original_uploader_in_current_and_fixed_versions(client):
    source = add_source(client)
    confirmed = client.post(
        f"/api/handover/records/{source['id']}/confirm",
        json={"version": 1, "actor": "后续审核人", "opinion": "审核意见"},
    )
    assert confirmed.status_code == 200, confirmed.text
    for suffix in ("", "?version=1", "?version=2"):
        response = client.get(f"/api/handover/records/{source['id']}{suffix}")
        assert response.status_code == 200
        row = response.json()
        assert row["created_by"] == "上传整理人"
        assert row["payload"] == source["payload"]
    assert (
        client.get(f"/api/handover/sources/{source['id']}/original").content
        == source["payload"]["content"].encode()
    )


def test_replacing_source_retains_each_uploads_own_organizer(client):
    old = add_source(client, actor="原整理人")
    new = add_source(client, actor="新整理人", supersedes=old["id"], content="更新的原文")
    assert client.get(f"/api/handover/records/{old['id']}").json()["created_by"] == "原整理人"
    assert client.get(f"/api/handover/records/{new['id']}").json()["created_by"] == "新整理人"
    assert (
        client.get(f"/api/handover/records/{old['id']}?version=1").json()["payload"]
        == old["payload"]
    )


def test_regular_reader_sees_upload_organizer_without_private_review_history(client):
    source = add_source(client)
    confirmed = client.post(
        f"/api/handover/records/{source['id']}/confirm",
        json={"version": 1, "actor": "PRIVATE-REVIEW-ACTOR", "opinion": "PRIVATE-REVIEW-OPINION"},
    )
    assert confirmed.status_code == 200, confirmed.text
    accounts = json.loads(client.app.state.auth.initial_accounts.read_text(encoding="utf-8"))
    ordinary = next(account for account in accounts if account["username"] == "user")
    login = client.post(
        "/api/auth/login", json={"username": ordinary["username"], "password": ordinary["password"]}
    )
    assert login.status_code == 200
    client.headers["X-Arks-CSRF"] = login.json()["csrf_token"]
    response = client.get(f"/api/handover/records/{source['id']}")
    assert response.status_code == 200
    assert response.json()["created_by"] == "上传整理人"
    assert "confirmation" not in response.json()
    assert "PRIVATE-REVIEW" not in response.text
    assert client.get(f"/api/handover/records/{source['id']}/history").status_code == 403
    assert client.get("/api/handover/events").status_code == 403
