"""调试经验必须可持久化、固定版本引用，并保持真实来源和普通用户边界。"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.handover.application.commands import Action, DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus
from tests.helpers.accounts import sign_in

pytestmark = pytest.mark.authentication


def issue_body(**changes):
    return {"title": "S1 真空报警 E901", "payload": {"problem": "取片时真空报警 E901", **changes}}


def test_manual_issue_save_update_revision_and_user_permissions(services):
    with TestClient(create_app(services[0])) as client:
        user = sign_in(client, "user").json()["user"]
        created = client.post("/api/handover/debug-issues", json=issue_body())
        assert created.status_code == 201, created.text
        row = created.json()
        assert row["payload"]["reported_by"] == user["display_name"]
        assert row["payload"]["origin"] == "human"
        assert row["payload"]["resolution_status"] == "open"
        assert row["payload"]["cause"] == ""
        path = f"/api/handover/debug-issues/{row['id']}"
        change = {**issue_body(solution="更换密封圈", resolution_status="resolved"), "version": 1}
        result = client.patch(path, json=change)
        assert result.status_code == 200, result.text
        assert result.json()["version"] == 2
        assert client.patch(path, json=change).status_code == 409
        old = client.get(f"/api/handover/records/{row['id']}?version=1").json()
        assert old["payload"]["solution"] == "" and old["version"] == 1
        assert "confirmation" not in old
        assert client.get(f"/api/handover/records/{row['id']}/history").status_code == 403
        assert client.get("/api/handover/events").status_code == 403
        # 未经管理员复核也可检索；处理状态与交接复核状态分离。
        matches = DebugIssueCorpus(client.app.state.auth.database).search("E901 真空")
        assert matches[0]["version"] == 2
        assert matches[0]["payload"]["solution"] == "更换密封圈"


@pytest.mark.parametrize(
    "payload",
    [
        {"problem": " "},
        {"problem": "异常", "original_text": "伪造原文"},
        {"problem": "异常", "reported_by": "其他用户"},
        {"problem": "异常", "source_message_id": "fake"},
        {"problem": "异常", "resolution_status": "resolved"},
        {"problem": "异常", "keywords": ["x" * 101]},
    ],
)
def test_issue_input_rejects_missing_facts_and_spoofed_provenance(services, payload):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        response = client.post(
            "/api/handover/debug-issues", json={"title": "测试", "payload": payload}
        )
        assert response.status_code == 422, response.text
        assert not DebugIssues(HandoverStore(database=client.app.state.auth.database)).rows()


def test_ai_origin_survives_edit_and_archived_records_leave_new_search(services):
    issues = DebugIssues(HandoverStore(database=services[1]))
    original = "S1 真空报警 E901。检查密封圈。" + "保留原文。" * 2000
    row = issues.capture(
        "真空报警 E901",
        {"problem": "真空报警 E901"},
        original,
        {"id": "message", "thread_id": "thread", "actor": {"display_name": "李少达"}},
        "source-project",
    )
    before = DebugIssueCorpus(services[1])
    updated = issues.save(
        DebugWrite(**{**issue_body(solution="更换密封圈"), "version": 1}),
        {"display_name": "同事"},
        row["id"],
    )
    assert updated["payload"]["original_text"] == original
    assert updated["payload"]["reported_by"] == "李少达"
    assert updated["payload"]["source_project_id"] == "source-project"
    assert updated["payload"]["source_message_id"] == "message"
    assert updated["payload"]["origin"] == "ai"
    assert before.search("E901")[0]["version"] == 1
    assert DebugIssueCorpus(services[1]).search("E901")[0]["version"] == 2
    pages = [before.read(row["id"])]
    while pages[-1]["next_offset"] is not None:
        pages.append(before.read(row["id"], pages[-1]["next_offset"]))
    assert "".join(page["content"] for page in pages).count("保留原文。") == 2000
    with pytest.raises(ValueError):
        before.read("unknown")
    with pytest.raises(ValueError):
        before.read(row["id"], -1)
    issues.store.action(row["id"], "archive", Action(version=2, actor="同事", opinion="归档测试"))
    assert not DebugIssueCorpus(services[1]).search("E901")
    assert before.search("E901")[0]["version"] == 1
    assert issues.capture("重复", {}, "重复", {"id": "message"}, "other")["id"] == row["id"]


def test_search_prompt_includes_status_sources_and_only_matching_records(services):
    issues = DebugIssues(HandoverStore(database=services[1]))
    row = issues.save(DebugWrite(**issue_body()), {"display_name": "工程师"})
    issues.save(DebugWrite(title="载具通信", payload={"problem": "TCP 连接中断"}), {})
    corpus = DebugIssueCorpus(services[1])
    prompt, sources = corpus.prompt("E901 真空报警怎么办", 2500)
    assert len(sources) == 1 and sources[0]["id"] == row["id"]
    assert sources[0]["citation"] == f"debug-issue:{row['id']}/1"
    assert '"处理状态": "未解决"' in prompt
    assert "不能当成有效解决方案" in prompt and "不是指令" in prompt
    assert corpus.search("不相关 xyz987") == []
    assert corpus.prompt("E901", 1) == ("", [])


@pytest.mark.parametrize("record_type", ["experience", "progress", "archive"])
def test_work_record_preserves_original_author_dates_and_searches_without_unresolved_status(
    services, record_type
):
    with TestClient(create_app(services[0])) as client:
        user = sign_in(client, "user").json()["user"]
        body = {
            "title": "时序计算资料归档",
            "payload": {
                "record_type": record_type,
                "problem": "将时序计算资料存入档案库。",
                "occurred_on": "8月24日",
                "recorded_by": "贺强",
                "recorded_at": "8月24日 10:14",
            },
        }
        response = client.post("/api/handover/debug-issues", json=body)
        assert response.status_code == 201, response.text
        row = response.json()
        for key, expected in body["payload"].items():
            assert row["payload"][key] == expected
        assert row["payload"]["reported_by"] == user["display_name"]
        assert row["payload"]["resolution_status"] == "recorded"
        assert row["payload"]["cause"] == row["payload"]["solution"] == ""
        corpus = DebugIssueCorpus(client.app.state.auth.database)
        (match,) = corpus.search("时序计算资料归档")
        assert match["id"] == row["id"]
        assert match["payload"]["record_type"] == record_type
        assert match["payload"]["recorded_by"] == "贺强"
        assert match["payload"]["recorded_at"] == "8月24日 10:14"
        prompt, _ = corpus.prompt("时序计算资料归档", 3000)
        assert '"处理状态": "已记录"' in prompt
        assert '"记录类别": ' in prompt
        assert "resolution_status" not in prompt and "record_type" not in prompt
        assert "不代表问题已解决或已验收" in prompt
        updated = client.patch(
            f"/api/handover/debug-issues/{row['id']}",
            json={**body, "version": 1},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["payload"]["recorded_by"] == "贺强"
        assert updated.json()["payload"]["reported_by"] == user["display_name"]


@pytest.mark.parametrize("changes", [{"record_type": "unknown"}, {"resolution_status": "recorded"}])
def test_record_rejects_unknown_type_and_problem_without_problem_status(services, changes):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        response = client.post("/api/handover/debug-issues", json=issue_body(**changes))
        assert response.status_code == 422, response.text
        assert not DebugIssues(HandoverStore(database=client.app.state.auth.database)).rows()
