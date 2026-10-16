"""直接文本导入保留原文、来源和历史，并复用既有交接资料流程。"""

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(services):
    with TestClient(create_app(services[0])) as value:
        yield value


def save_text(client, content="测试记录", **changes):
    return client.post(
        "/api/handover/sources/text",
        json={"title": "测试日志", "actor": "整理人", "content": content, **changes},
    )


def test_text_source_keeps_exact_original_metadata_and_evidence(client):
    content = "  项目日志\u00a0测试\r\n\r\n不同高度切换焦距，中心点发生变化。\n尾部缩进  \n"
    response = save_text(
        client,
        content,
        title="  会议/日志:α  ",
        actor=" 整理人 ",
        provider="记录作者",
        source_version="2026-10-14",
        device="ZX2200",
        notes="来源：测试会议纪要；只用于功能验证。",
    )
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["title"] == "会议/日志:α"
    assert row["kind"] == "source" and row["state"] == "draft" and row["version"] == 1
    assert row["scope_id"] == "global" and row["source_project_id"] is None
    assert row["payload"]["content"] == content
    assert row["payload"]["format"] == "text" and row["payload"]["origin"] == "human"
    assert row["payload"]["parse_status"] == "readable"
    assert row["payload"]["filename"] == "会议_日志_α.txt"
    assert row["payload"]["notes"] == "来源：测试会议纪要；只用于功能验证。"
    assert row["payload"]["provider"] == "记录作者"
    assert row["payload"]["sha256"] == hashlib.sha256(content.encode()).hexdigest()
    original = client.get(f"/api/handover/sources/{row['id']}/original")
    assert original.content == content.encode()
    assert original.headers["content-type"].startswith("text/plain")
    events = client.get("/api/handover/events").json()
    assert events[0]["actor"] == "整理人" and events[0]["action"] == "created"
    # 文本保存为普通资料记录，后续工作可引用其固定版本及逐字原句。
    linked = client.post(
        "/api/handover/records",
        json={
            "kind": "task",
            "title": "核对记录中的工况",
            "actor": "整理人",
            "payload": {
                "evidence": [
                    {
                        "record_id": row["id"],
                        "version": 1,
                        "quote": "不同高度切换焦距，中心点发生变化。",
                    }
                ],
            },
        },
    )
    assert linked.status_code == 201, linked.text


@pytest.mark.parametrize(
    "changes",
    [
        {"title": " \t "},
        {"actor": "　 "},
        {"content": "\r\n \t　"},
        {"content": "字" * 100001},
        {"title": "字" * 201},
        {"notes": "字" * 2001},
        {"source_project_id": "unsupported"},
        {"origin": "ai"},
    ],
)
def test_text_source_rejects_invalid_input_without_writing(client, changes):
    before = client.get("/api/handover").json()
    assert save_text(client, **changes).status_code == 422
    assert client.get("/api/handover").json() == before
    assert client.get("/api/handover/events").json() == []


def test_text_source_accepts_limit_without_truncation(client):
    content = "字" * 99999 + "😀"
    row = save_text(client, content).json()
    assert row["payload"]["content"] == content
    assert len(row["payload"]["content"]) == 100000
    assert row["payload"]["parse_status"] == "readable"
    assert client.get(f"/api/handover/sources/{row['id']}/original").content == content.encode()


def test_text_replacement_keeps_old_blob_and_fixed_version(client):
    old = client.post(
        "/api/handover/sources/import",
        params={"filename": "旧资料.txt", "actor": "整理人"},
        content="旧原文\r\n版本一".encode(),
    ).json()
    replacement = save_text(
        client,
        "补充后的原文\n版本二",
        supersedes=old["id"],
        source_version="第二版",
    )
    assert replacement.status_code == 201, replacement.text
    current = replacement.json()
    assert current["id"] != old["id"] and current["payload"]["supersedes"] == old["id"]
    assert (
        client.get(f"/api/handover/sources/{old['id']}/original").content
        == "旧原文\r\n版本一".encode()
    )
    assert (
        client.get(f"/api/handover/records/{old['id']}?version=1").json()["payload"]
        == old["payload"]
    )
    assert (
        client.get(f"/api/handover/sources/{current['id']}/original").content
        == "补充后的原文\n版本二".encode()
    )


def test_text_source_survives_reopening_app(services):
    with TestClient(create_app(services[0])) as first:
        row = save_text(first, "重启后仍须完整保留的文本").json()
    with TestClient(create_app(services[0])) as reopened:
        assert (
            reopened.get(f"/api/handover/records/{row['id']}").json()["payload"]["content"]
            == "重启后仍须完整保留的文本"
        )
        assert (
            reopened.get(f"/api/handover/sources/{row['id']}/original").content.decode()
            == "重启后仍须完整保留的文本"
        )


def test_file_upload_keeps_source_notes_and_existing_behavior(client):
    response = client.post(
        "/api/handover/sources/import",
        params={"filename": "外部资料.txt", "actor": "整理人", "notes": "来自外部会议记录"},
        content="附件原文".encode(),
    )
    assert response.status_code == 201, response.text
    assert response.json()["title"] == "外部资料.txt"
    assert response.json()["payload"]["notes"] == "来自外部会议记录"
    assert response.json()["payload"]["content"] == "附件原文"
