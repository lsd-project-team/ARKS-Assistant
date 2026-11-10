"""审核拒绝的不可变历史、版本竞争、下游复核及重新提交。"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(services):
    with TestClient(create_app(services[0])) as value:
        yield value


def source(client, title="审核原文", **metadata):
    response = client.post(
        "/api/handover/sources/text",
        json={
            "title": title,
            "content": "保留原文、缩进与换行。\n  第二行。",
            "actor": "整理人",
            **metadata,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def review(client, row, decision="reject", **body):
    return client.post(
        f"/api/handover/records/{row['id']}/{decision}",
        json={
            "version": row["version"],
            "actor": "审核人",
            "opinion": "现象描述需要补充实际工况",
            **body,
        },
    )


def test_rejection_preserves_original_and_records_reviewer_reason_and_history(client):
    row = source(client)
    original = client.get(f"/api/handover/sources/{row['id']}/original").content
    result = review(client, row)
    assert result.status_code == 200, result.text
    rejected = result.json()
    assert rejected["state"] == "rejected" and rejected["version"] == 2
    assert rejected["payload"] == row["payload"]
    saved = client.get(f"/api/handover/records/{row['id']}").json()
    assert saved["confirmation"]["decision"] == "reject"
    assert saved["confirmation"]["actor"] == "审核人"
    assert saved["confirmation"]["opinion"] == "现象描述需要补充实际工况"
    assert saved["confirmation"]["time"] == rejected["updated_at"]
    assert client.get(f"/api/handover/sources/{row['id']}/original").content == original
    old = client.get(f"/api/handover/records/{row['id']}?version=1").json()
    assert old["payload"] == row["payload"] and old["state"] == "draft"
    history = client.get(f"/api/handover/records/{row['id']}/history").json()
    assert [item["state"] for item in history] == ["rejected", "draft"]
    events = client.get("/api/handover/events").json()
    assert events[0]["action"] == "reject" and events[0]["actor"] == "审核人"
    assert review(client, rejected).status_code == 409
    assert review(client, rejected, "confirm").status_code == 409
    assert review(client, row, "confirm").status_code == 409
    replacement = source(client, "补充后的原文", supersedes=row["id"])
    assert review(client, replacement, "confirm").status_code == 200


@pytest.mark.parametrize(
    "body", [{"actor": " "}, {"opinion": " "}, {"opinion": ""}, {"content": "篡改原文"}]
)
def test_invalid_rejection_cannot_write_history(client, body):
    row = source(client)
    assert review(client, row, **body).status_code == 422
    saved = client.get(f"/api/handover/records/{row['id']}").json()
    assert saved["version"] == 1 and saved["state"] == "draft"


def test_rejected_source_invalidates_confirmed_dependents_and_prevents_confirmation(client):
    raw = source(client)
    response = client.post(
        "/api/handover/records",
        json={
            "kind": "issue",
            "title": "引用原文的说明",
            "actor": "整理人",
            "payload": {
                "question": "保留说明原文。",
                "evidence": [{"record_id": raw["id"], "version": 1}],
            },
        },
    )
    assert response.status_code == 201, response.text
    note = response.json()
    assert review(client, note, "confirm").status_code == 200
    assert review(client, raw).status_code == 200
    current = client.get(f"/api/handover/records/{note['id']}").json()
    assert current["state"] == "needs_review" and current["version"] == 3
    denied = review(client, current, "confirm")
    assert denied.status_code == 409 and "关联内容已被拒绝" in denied.text
    rejected = client.get(f"/api/handover/records/{raw['id']}").json()
    assert rejected["state"] == "rejected"


def test_edit_after_rejection_can_be_reviewed_without_changing_rejected_version(client):
    created = client.post(
        "/api/handover/records",
        json={
            "kind": "issue",
            "title": "待补充的说明",
            "actor": "整理人",
            "payload": {"question": "原说明"},
        },
    ).json()
    rejected = review(client, created).json()
    updated = client.patch(
        f"/api/handover/records/{created['id']}",
        json={
            "kind": "issue",
            "title": created["title"],
            "actor": "整理人",
            "version": rejected["version"],
            "payload": {**created["payload"], "question": "补充实际工况的说明"},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["state"] == "draft"
    assert review(client, updated.json(), "confirm").status_code == 200
    old = client.get(f"/api/handover/records/{created['id']}?version=2").json()
    assert old["state"] == "rejected" and old["payload"]["question"] == "原说明"


@pytest.mark.parametrize("terminal", ["confirm", "archive"])
def test_rejection_cannot_overwrite_completed_or_archived_state(client, terminal):
    raw = source(client)
    completed = review(client, raw, terminal)
    assert completed.status_code == 200
    assert review(client, completed.json()).status_code == 409


def test_confirmation_refuses_stale_evidence_without_writing_result(client):
    raw = source(client)
    note = client.post(
        "/api/handover/records",
        json={
            "kind": "issue",
            "title": "来源已经更新的说明",
            "actor": "整理人",
            "payload": {
                "question": "原说明",
                "evidence": [{"record_id": raw["id"], "version": 1}],
            },
        },
    ).json()
    assert review(client, raw, "confirm").status_code == 200
    result = review(client, note, "confirm")
    assert result.status_code == 409 and "来源有新版本" in result.text
    current = client.get(f"/api/handover/records/{note['id']}").json()
    assert current["state"] == "draft" and current["version"] == 1
