"""移除提取工作流后，旧接口不再生效，资料检索及固定历史版本继续可读。"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.handover.domain.schemas import validate_payload
from app.modules.handover.infrastructure.persistence.models import HandoverRecord, HandoverRevision
from app.modules.knowledge.corpora.handover_materials import HandoverMaterialCorpus
from tests.helpers.accounts import sign_in

pytestmark = pytest.mark.authentication


@pytest.mark.parametrize("username", ["admin", "user"])
def test_removed_ai_routes_cannot_create_jobs_or_merge_candidates(services, username):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, username)
        response = client.post(
            "/api/handover/sources/text",
            json={"title": "原始资料", "content": "保留资料正文供后续检索。", "actor": "整理人"},
        )
        assert response.status_code == 201, response.text
        source = response.json()
        before = client.get("/api/handover").json()
        for action in ("extract", "plan", "framework", "training"):
            response = client.post(
                "/api/handover/ai",
                json={"action": action, "record_ids": [source["id"]], "actor": "整理人"},
            )
            assert response.status_code == 404, response.text
            assert response.json()["detail"] == "接口不存在"
        for path in ("/ai/old-job/cancel", "/candidates/old-candidate/promote"):
            assert client.post("/api/handover" + path, json={}).status_code == 404
        assert not hasattr(client.app.state, "handover_ai")
        assert client.get("/api/handover").json() == before
        assert client.get(f"/api/handover/sources/{source['id']}/original").content.decode() == (
            "保留资料正文供后续检索。"
        )
        corpus = HandoverMaterialCorpus(client.app.state.auth.database)
        assert corpus.excerpt(source["id"])["content"] == "1: 保留资料正文供后续检索。"


def test_retired_records_are_read_only_and_do_not_appear_in_workbench(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "admin")
        database = client.app.state.auth.database
        # 模拟旧版留下的记录，避免通过已经移除的生产录入路径造测试数据。
        legacy = {
            "candidate": {"target_kind": "task", "proposed": {"goal": "旧候选"}},
            "job": {"action": "extract", "record_ids": ["old-source"], "status": "interrupted"},
        }
        with database.session.begin() as session:
            for kind, payload in legacy.items():
                identifier = "legacy-" + kind
                value = json.dumps(validate_payload(kind, payload), ensure_ascii=False)
                session.add(
                    HandoverRecord(id=identifier, kind=kind, title="旧记录", payload_json=value)
                )
                session.flush()
                session.add(
                    HandoverRevision(
                        record_id=identifier,
                        version=1,
                        title="旧记录",
                        state="draft",
                        payload_json=value,
                    )
                )
        assert client.get("/api/handover").json()["records"] == []
        for kind in legacy:
            identifier = "legacy-" + kind
            response = client.get(f"/api/handover/records/{identifier}?version=1")
            assert response.status_code == 200, response.text
            assert response.json()["version"] == 1
            body = {
                "kind": kind,
                "title": "不能改写",
                "actor": "整理人",
                "version": 1,
                "payload": legacy[kind],
            }
            assert client.patch(f"/api/handover/records/{identifier}", json=body).status_code == 409
            assert client.post("/api/handover/records", json=body).status_code == 409
            for action in ("archive", "restore", "confirm", "reject"):
                result = client.post(
                    f"/api/handover/records/{identifier}/{action}",
                    json={"version": 1, "actor": "整理人", "opinion": "不能操作历史作业"},
                )
                assert result.status_code == 409, result.text
            assert client.get(f"/api/handover/records/{identifier}").json()["title"] == "旧记录"
