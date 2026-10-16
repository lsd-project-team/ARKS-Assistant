"""简化工作清单使用现有记录接口，保存进度不要求交接确认。"""

from fastapi.testclient import TestClient

from app.main import create_app


def test_minimal_work_item_and_direct_status_updates(services):
    with TestClient(create_app(services[0])) as client:
        response = client.post(
            "/api/handover/records",
            json={
                "kind": "task",
                "title": "核查参数保存",
                "payload": {},
                "actor": "本机用户（未填写姓名）",
            },
        )
        assert response.status_code == 201, response.text
        row = response.json()
        assert row["payload"]["work_status"] == "todo"
        for status in ["doing", "blocked", "done"]:
            response = client.patch(
                f"/api/handover/records/{row['id']}",
                json={
                    "kind": "task",
                    "title": row["title"],
                    "version": row["version"],
                    "payload": {
                        **row["payload"],
                        "work_status": status,
                        "notes": f"进度：{status}",
                    },
                    "actor": "本机用户（未填写姓名）",
                    "reason": "更新工作进度",
                },
            )
            assert response.status_code == 200, response.text
            row = response.json()
        assert row["payload"]["work_status"] == "done"
        assert row["state"] == "draft"
        assert row.get("confirmation", {}) == {}
        history = client.get(f"/api/handover/records/{row['id']}/history").json()
        assert len(history) == 4
        first = client.get(f"/api/handover/records/{row['id']}?version=1").json()
        assert first["payload"]["work_status"] == "todo"


def test_legacy_fields_survive_progress_change_and_stale_edits_are_rejected(services):
    with TestClient(create_app(services[0])) as client:
        row = client.post(
            "/api/handover/records",
            json={
                "kind": "task",
                "title": "已有工作",
                "actor": "整理人",
                "payload": {
                    "current": "原有现状",
                    "acceptance": "原有标准",
                    "result": "历史结果",
                    "work_status": "accepted",
                    "priority": "high",
                    "category": "bug",
                },
            },
        ).json()
        body = {
            "kind": "task",
            "title": row["title"],
            "version": row["version"],
            "payload": {**row["payload"], "owner": "负责人", "notes": "最新备注"},
            "actor": "整理人",
        }
        response = client.patch(f"/api/handover/records/{row['id']}", json=body)
        assert response.status_code == 200, response.text
        updated = response.json()
        for key in ["current", "acceptance", "result", "priority", "category", "work_status"]:
            assert updated["payload"][key] == row["payload"][key]
        assert client.patch(f"/api/handover/records/{row['id']}", json=body).status_code == 409
        stored = client.get(f"/api/handover/records/{row['id']}").json()
        assert stored["payload"]["notes"] == "最新备注"
