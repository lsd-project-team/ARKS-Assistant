"""三项问答契约、metadata权限和检索正文边界。"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus
from app.modules.knowledge.documents import knowledge_document
from app.modules.knowledge.search import searchable_text
from app.modules.knowledge.semantic import SemanticRetrieval
from tests.helpers.accounts import sign_in


def body(**metadata):
    return {
        "title": "取片经验",
        "payload": {
            "question": "取片报警E901如何处理？",
            "answer": "在S1加热工况下，可检查真空管路并更换密封圈。",
            "keywords": ["E901", "真空", "取片"],
            "metadata": {
                "recorded_by": "metadata-only-author",
                "recorded_at": "8月24日",
                **metadata,
            },
        },
    }


def test_document_metadata_never_enters_default_reading_or_embedding(services):
    saved = DebugIssues(HandoverStore(database=services[1])).save(DebugWrite(**body()), {})
    assert set(saved["payload"]) == {"question", "answer", "keywords", "metadata"}
    document = knowledge_document(saved)
    assert document.metadata["recorded_by"] == "metadata-only-author"
    assert document.metadata["version"] == 1
    assert all(word in document.page_content for word in ("取片报警E901", "更换密封圈", "真空"))
    assert "metadata-only-author" not in document.page_content
    assert "8月24日" not in searchable_text(saved)[1]
    corpus = DebugIssueCorpus(services[1])
    content = corpus.review_records({saved["id"]: 1})[0]["content"]
    assert set(content) == {"问题", "答案", "关键词"}
    assert "metadata-only-author" not in json.dumps(content)
    requested = DebugIssueCorpus(services[1], context_query="这条记录是谁记录的？")
    assert (
        requested.review_records({saved["id"]: 1})[0]["content"]["原记录人"]
        == "metadata-only-author"
    )


async def test_search_tool_only_expands_requested_author_metadata(services, monkeypatch):
    monkeypatch.setattr(SemanticRetrieval, "scores", lambda *_: {})
    DebugIssues(HandoverStore(database=services[1])).save(DebugWrite(**body()), {})
    search = next(
        tool for tool in DebugIssueCorpus(services[1]).tools() if tool.name == "search_debug_issues"
    )
    normal = json.loads(await search.ainvoke({"query": "E901"}))
    assert "metadata-only-author" not in json.dumps(normal)
    requested = json.loads(await search.ainvoke({"query": "E901是谁记录的？"}))
    assert requested["matches"][0]["payload"]["原记录人"] == "metadata-only-author"


@pytest.mark.authentication
def test_qa_edit_preserves_provenance_and_old_reference(services):
    with TestClient(create_app(services[0])) as client:
        user = sign_in(client, "user").json()["user"]
        response = client.post(
            "/api/handover/debug-issues", json=body(cause="旧原因判断", verification="旧结果说明")
        )
        assert response.status_code == 201, response.text
        saved = response.json()
        original = saved["payload"]["metadata"]["original_text"]
        assert saved["payload"]["metadata"]["reported_by"] == user["display_name"]
        update = body(recorded_by="原作者", resolution_status="resolved")
        update["payload"]["answer"] = "更换密封圈后，连续取片20次正常。"
        response = client.patch(
            f"/api/handover/debug-issues/{saved['id']}", json={**update, "version": 1}
        )
        assert response.status_code == 200, response.text
        current = response.json()
        assert current["payload"]["metadata"]["original_text"] == original
        assert current["payload"]["metadata"]["cause"] == "旧原因判断"
        assert current["payload"]["metadata"]["verification"] == "旧结果说明"
        old = client.get(f"/api/handover/records/{saved['id']}?version=1").json()
        assert old["payload"]["answer"] == saved["payload"]["answer"]
        assert current["payload"]["answer"] == update["payload"]["answer"]
        assert (
            client.patch(
                f"/api/handover/debug-issues/{saved['id']}", json={**update, "version": 1}
            ).status_code
            == 409
        )


@pytest.mark.authentication
@pytest.mark.parametrize("field", ["original_text", "reported_by", "images", "source_message_id"])
def test_client_cannot_spoof_source_metadata(services, field):
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        value = body()
        value["payload"]["metadata"][field] = [] if field == "images" else "forged"
        response = client.post("/api/handover/debug-issues", json=value)
        assert response.status_code == 422
        assert not DebugIssues(HandoverStore(database=services[1])).rows()
