"""文字检索带出固定版本原图，重复位置、旧引用和权限均不能丢失。"""

import base64
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import Paths
from app.infrastructure.database.session import Database
from app.infrastructure.storage.backup import create_backup
from app.infrastructure.storage.restore import restore_backup
from app.infrastructure.storage.validation import validate_backup
from app.main import create_app
from app.modules.handover.infrastructure.persistence.models import HandoverDebugImage
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus
from tests.helpers.accounts import sign_in

pytestmark = pytest.mark.authentication

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII="
)
GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
BODY = {"title": "adv-3 降温试验", "payload": {"problem": "室温23.2℃，adv-3贴片精度−4～2μm。"}}


def upload(client, row, data=PNG, **query):
    return client.post(
        f"/api/handover/debug-issues/{row['id']}/images",
        params={"version": row["version"], "filename": "原图.png", **query},
        content=data,
        headers={"Content-Type": "application/octet-stream"},
    )


def image_url(row, index, version=None):
    return f"/api/handover/debug-issues/{row['id']}/images/{version or row['version']}/{index}"


def test_original_images_keep_bytes_duplicate_positions_and_fixed_versions(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        row = client.post("/api/handover/debug-issues", json=BODY).json()
        assert row["payload"]["metadata"]["original_text"] == BODY["payload"]["problem"]
        for data in (PNG, PNG, GIF):
            response = upload(client, row, data, recorded_at="2026年7月27日16:09")
            assert response.status_code == 201, response.text
            row = response.json()
        assert row["version"] == 4
        images = row["payload"]["metadata"]["images"]
        assert len(images) == 3
        assert images[0] == images[1]
        assert images[0]["id"] != images[2]["id"]
        assert images[0]["recorded_at"] == "2026年7月27日16:09"
        for index, data in enumerate((PNG, PNG, GIF)):
            response = client.get(image_url(row, index))
            assert response.status_code == 200
            assert response.content == data
            assert response.headers["content-type"] == ("image/gif" if index == 2 else "image/png")
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["cache-control"] == "no-store"
        assert client.get(image_url(row, 0, 1)).status_code == 404
        assert client.get(image_url(row, 1, 2)).status_code == 404
        assert client.get(image_url(row, 0, 2)).content == PNG
        stale = upload(client, {**row, "version": 2})
        assert stale.status_code == 409
        with services[1].session() as session:
            assert session.scalar(select(func.count()).select_from(HandoverDebugImage)) == 2
        # 编辑正文不修改图片快照，检索上下文始终引用创建时看到的版本。
        old = DebugIssueCorpus(services[1])
        changed = client.patch(
            f"/api/handover/debug-issues/{row['id']}",
            json={**BODY, "version": 4, "payload": {"problem": "adv-3 新的文字记录"}},
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["payload"]["metadata"]["images"] == images
        assert changed.json()["payload"]["metadata"]["original_text"] == BODY["payload"]["problem"]
        assert old.search("adv-3")[0]["version"] == 4
        assert DebugIssueCorpus(services[1]).search("adv-3")[0]["version"] == 5
        assert client.get(image_url(row, 0)).content == PNG


def test_search_returns_original_image_metadata_without_vision_or_image_indexing(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        row = client.post("/api/handover/debug-issues", json=BODY).json()
        row = upload(client, row, filename="zebraonlyimage.png").json()
        feedback = []
        corpus = DebugIssueCorpus(services[1], lambda kind, value: feedback.append((kind, value)))
        prompt, sources = corpus.prompt("adv-3 降温试验", 2500)
        assert sources[0]["image_count"] == 1
        assert "本轮未识别图片" in prompt
        assert "zebraonlyimage" not in prompt
        assert not corpus.search("zebraonlyimage")
        corpus.read(row["id"])
        references = [value for kind, value in feedback if kind == "knowledge_reference"]
        assert references and all(value["image_count"] == 1 for value in references)
        assert all(value["version"] == 2 for value in references)
        archived = client.post(
            f"/api/handover/records/{row['id']}/archive",
            json={"version": 2, "actor": "用户", "opinion": "归档"},
        )
        assert archived.status_code == 200, archived.text
        assert not DebugIssueCorpus(services[1]).search("adv-3")
        assert client.get(image_url(row, 0)).content == PNG
        assert upload(client, {**row, "version": 3}).status_code == 409


async def test_read_tool_keeps_complete_business_text_without_image_or_source_internals(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        problem = "7月23日09:00—7月24日16:30，室温25.2℃，精度3μm 3Σ。\n" * 180
        row = client.post(
            "/api/handover/debug-issues",
            json={"title": "7月23—24日｜adv-3 试验", "payload": {"problem": problem}},
        ).json()
        for _ in range(3):
            row = upload(client, row, filename="internal-only.png").json()
        corpus = DebugIssueCorpus(services[1], context_query="adv-3 7月23日试验")
        read_tool = next(tool for tool in corpus.tools() if tool.name == "read_debug_issue")
        chunks = []
        offset = 0
        while offset is not None:
            page = json.loads(await read_tool.ainvoke({"record_id": row["id"], "offset": offset}))
            assert page["version"] == 4 and page["image_count"] == 3
            assert page["reference"] == (f"[7月23—24日｜adv-3 试验](debug-issue:{row['id']}/4)")
            assert "只展示AI回复的文字和回答实际引用记录的全部原图" in page["display_hint"]
            assert "只展示对应记录" in page["display_hint"]
            assert "不要声称无法展示原图" in page["display_hint"]
            chunks.append(page["content"])
            offset = page["next_offset"]
        assert len(chunks) > 1
        content = json.loads("".join(chunks))
        assert content["问题"] == problem.strip()
        assert "录入原文" not in content
        assert set(content) == {"问题", "答案"}
        original_corpus = DebugIssueCorpus(services[1], context_query="请逐字读取原文")
        original_chunks = []
        offset = 0
        while offset is not None:
            page = original_corpus.read(row["id"], offset)
            original_chunks.append(page["content"])
            offset = page["next_offset"]
        assert json.loads("".join(original_chunks))["录入原文"] == problem
        assert (
            not {"images", "origin", "evidence", "reported_by", "source_thread_id"} & content.keys()
        )
        assert "internal-only.png" not in "".join(chunks)
        assert row["payload"]["metadata"]["images"][0]["id"] not in "".join(chunks)
        assert "resolution_status" not in "".join(chunks)
        search_tool = next(tool for tool in corpus.tools() if tool.name == "search_debug_issues")
        searched = json.loads(await search_tool.ainvoke({"query": "adv-3 试验"}))
        assert searched["matches"][0]["metadata"]["处理状态"] == "未解决"
        assert searched["matches"][0]["metadata"]["记录类别"] == "问题处理"
        prompt, _ = corpus.prompt("adv-3 试验", 3000)
        assert "resolution_status" not in prompt and "record_type" not in prompt
        assert prompt.index("</debug_issue_records>") < prompt.index("只展示对应记录")
        # 精简的是模型读到的投影，记录原件及三处重复图片保持不变。
        saved = client.get(f"/api/handover/records/{row['id']}?version=4").json()
        assert saved["payload"] == row["payload"]


def test_adv_device_condition_keeps_other_machine_images_out_of_matches(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        rows = {}
        for device in ("adv-3", "adv-10", "adv-1"):
            body = {
                "title": f"{device} 精度试验",
                "payload": {"problem": "室温23.2℃贴片精度试验", "device": device},
            }
            row = client.post("/api/handover/debug-issues", json=body).json()
            rows[device] = upload(client, row).json()
        corpus = DebugIssueCorpus(services[1], context_query="adv-3 精度试验")
        report = corpus.search_report("贴片精度")
        assert [item["id"] for item in report["matches"]] == [rows["adv-3"]["id"]]
        assert {item["id"] for item in report["excluded_records"]} == {
            rows["adv-10"]["id"],
            rows["adv-1"]["id"],
        }
        other = DebugIssueCorpus(services[1]).search("adv-1 精度试验")
        assert [item["id"] for item in other] == [rows["adv-1"]["id"]]


@pytest.mark.parametrize(
    ("data", "filename"),
    [(b"", "empty.png"), (b"<svg onload='alert(1)'/>", "evil.svg"), (PNG, "bad\nname.png")],
)
def test_invalid_image_upload_does_not_change_record_or_store_bytes(services, data, filename):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        row = client.post("/api/handover/debug-issues", json=BODY).json()
        assert upload(client, row, data, filename=filename).status_code == 409
        current = client.get(f"/api/handover/records/{row['id']}").json()
        assert current["version"] == 1 and current["payload"]["metadata"]["images"] == []
        with services[1].session() as session:
            assert session.scalar(select(func.count()).select_from(HandoverDebugImage)) == 0


def test_image_endpoints_require_login_and_csrf_and_are_record_scoped(services):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        row = client.post("/api/handover/debug-issues", json=BODY).json()
        row = upload(client, row).json()
        other = client.post("/api/handover/debug-issues", json=BODY).json()
        assert client.get(image_url(other, 0)).status_code == 404
        assert client.get(image_url(row, -1)).status_code == 404
        client.headers.pop("X-Arks-CSRF")
        assert upload(client, row).status_code == 403
        client.cookies.clear()
        assert client.get(image_url(row, 0)).status_code == 401
        assert upload(client, row).status_code == 401


def test_sqlite_backup_restore_keeps_record_text_and_every_original_image(services, tmp_path):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        row = client.post("/api/handover/debug-issues", json=BODY).json()
        for data in (PNG, PNG, GIF):
            row = upload(client, row, data).json()
        backup = create_backup(services[0])
        report = validate_backup(backup)
        with client.app.state.auth.database.engine.connect() as connection:
            revision = connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
        assert report["valid"] and report["database_revision"] == revision
    restored = Paths(tmp_path / "restored", services[0].workspace)
    restore_backup(backup, restored.data)
    database = Database(restored.data / "app.sqlite3")
    try:
        store = HandoverStore(database=database)
        saved = store.get(row["id"], row["version"])
        assert saved["payload"] == row["payload"]
        assert [store.debug_image(row["id"], row["version"], i)["content"] for i in range(3)] == [
            PNG,
            PNG,
            GIF,
        ]
    finally:
        database.close()
