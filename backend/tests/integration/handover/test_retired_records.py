"""移除提取工作流后，旧接口和停用记录类型不再生效，当前资料与原始历史数据保留。"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from app.modules.handover.infrastructure.persistence.models import (
    HandoverBlob,
    HandoverEvent,
    HandoverRecord,
    HandoverRevision,
)
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


def stored_records(database):
    with database.engine.connect() as connection:
        return {
            name: list(connection.execute(text(f'SELECT * FROM "{name}"')))
            for name in (
                "handover_records",
                "handover_revisions",
                "handover_events",
                "handover_blobs",
            )
        }


def test_retired_types_have_no_read_write_or_reference_routes_and_preserve_storage(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "admin")
        database = client.app.state.auth.database
        legacy = {
            "interview": {"transcript": "旧原文", "author": "原作者"},
            "candidate": {"target_kind": "task", "proposed": {"goal": "旧候选"}},
            "job": {"action": "extract", "record_ids": ["old-source"], "status": "interrupted"},
        }
        with database.session.begin() as session:
            for kind, payload in legacy.items():
                identifier = "legacy-" + kind
                value = json.dumps(payload, ensure_ascii=False)
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
                session.add(
                    HandoverEvent(
                        record_id=identifier,
                        action="created",
                        actor="旧整理人",
                        detail="历史快照",
                        version=1,
                    )
                )
                session.add(
                    HandoverBlob(
                        record_id=identifier,
                        name="原附件.txt",
                        media_type="text/plain",
                        sha256="old",
                        content=b"original bytes",
                    )
                )
        before = stored_records(database)
        assert client.get("/api/handover").json()["records"] == []
        assert client.get("/api/handover/events").json() == []
        schema = client.get("/api/handover/schema").json()
        assert not set(legacy) & schema["kinds"].keys()
        assert not set(legacy) & schema["schemas"].keys()
        assert HandoverMaterialCorpus(database).search("旧原文") == []
        for kind, payload in legacy.items():
            identifier = "legacy-" + kind
            route = f"/api/handover/records/{identifier}"
            for suffix in ("", "?version=1", "/history"):
                assert client.get(route + suffix).status_code == 404
            assert client.get(f"/api/handover/sources/{identifier}/original").status_code == 404
            body = {
                "kind": kind,
                "title": "不能改写",
                "actor": "整理人",
                "version": 1,
                "payload": payload,
            }
            assert client.patch(route, json=body).status_code == 422
            assert client.post("/api/handover/records", json=body).status_code == 422
            for action in ("archive", "restore", "confirm", "reject"):
                response = client.post(
                    route + "/" + action,
                    json={
                        "version": 1,
                        "actor": "整理人",
                        "opinion": "不处理停用类型",
                    },
                )
                assert response.status_code == 404, response.text
            package = client.post(
                "/api/handover/packages",
                json={
                    "title": "不能导出旧记录",
                    "actor": "整理人",
                    "record_ids": [identifier],
                },
            )
            assert package.status_code == 404
            linked = client.post(
                "/api/handover/records",
                json={
                    "kind": "issue",
                    "title": "不能引用旧记录",
                    "actor": "整理人",
                    "payload": {
                        "question": "待核对",
                        "evidence": [{"record_id": identifier, "version": 1}],
                    },
                },
            )
            assert linked.status_code == 409
        assert stored_records(database) == before
