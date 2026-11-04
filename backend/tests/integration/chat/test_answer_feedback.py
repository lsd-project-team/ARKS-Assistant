"""真实登录、临时数据库验证反馈归属、版本、重试、校验和后台分页。"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import create_app
from app.modules.chat.models import AnswerFeedback, Message, Run
from app.modules.chat.runs import RunManager
from tests.helpers.accounts import sign_in

pytestmark = pytest.mark.authentication


@pytest.fixture
def feedback_client(services, monkeypatch):
    monkeypatch.setattr(RunManager, "start", lambda *_: None)
    with TestClient(create_app(services[0])) as client:
        user = sign_in(client, "user").json()["user"]
        project = client.post("/api/projects", json={"name": "反馈测试"}).json()["id"]
        prefix = f"/api/p/{project}"
        repo = client.app.state.projects.services(project).repository
        run = client.post(prefix + "/threads/start", json={"content": "原问题"}).json()
        repo.finish(run["id"], "原回答")
        answer = repo.run(run["id"])["response_message_id"]
        path = f"{prefix}/threads/{run['thread_id']}/messages/{answer}/feedback"
        yield client, repo, user, run, answer, path


def body(**extra):
    return {"submission_id": str(uuid4()), "content": "反馈说明", **extra}


def test_feedback_version_retry_admin_filter_and_page(feedback_client):
    client, repo, user, run, answer, path = feedback_client
    submitted = body(category="incorrect", content="  第一步有误\n请核对信号  ")
    response = client.post(path, json=submitted)
    assert response.status_code == 201, response.text
    assert response.json() == {"id": submitted["submission_id"]}
    assert client.post(path, json=submitted).json() == response.json()
    assert client.post(path, json={**submitted, "content": "改过的内容"}).status_code == 409
    # 在原回答之后追加重答，旧反馈不能转移到新版本。
    regenerated = repo.regenerate(run["id"])
    repo.finish(regenerated["id"], "新版回答")
    new_answer = repo.run(regenerated["id"])["response_message_id"]
    with repo.database.session() as session:
        rows = list(session.scalars(select(AnswerFeedback)))
        assert len(rows) == 1
        saved = rows[0]
        assert (saved.actor_id, saved.message_id, saved.run_id, saved.question_id) == (
            user["id"],
            answer,
            run["id"],
            run["message_id"],
        )
        assert saved.content == "第一步有误\n请核对信号"
        assert session.get(Message, answer).content == "原回答"
    assert client.get("/api/admin/questions").status_code == 403
    sign_in(client)
    empty = repo.create_run(None, "没有反馈的对话", [])
    repo.finish(empty["id"], "其他回答")
    listing = client.get("/api/admin/questions?has_feedback=true").json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == run["thread_id"]
    assert listing["items"][0]["feedback_count"] == 1
    assert client.get("/api/admin/questions?has_feedback=true&query=不存在").json()["total"] == 0
    assert client.get("/api/admin/questions?has_feedback=true&offset=1").json()["items"] == []
    detail_path = f"/api/admin/questions/{run['thread_id']}"
    detail = client.get(detail_path).json()
    assert detail["feedback"][0]["actor"]["id"] == user["id"]
    assert detail["feedback"][0]["category"] == "incorrect"
    assert detail["feedback"][0]["message_id"] != new_answer
    assert detail["feedback"][0]["created_at"]
    answer_index = next(i for i, item in enumerate(detail["messages"]) if item["id"] == answer)
    assert client.get(detail_path + "?limit=1").json()["feedback"] == []
    page = client.get(detail_path + f"?offset={answer_index}&limit=1").json()
    assert [item["id"] for item in page["feedback"]] == [submitted["submission_id"]]
    # 只回收不丢反馈，永久删除时沿现有对话外键一并清理。
    repo.catalog.change(run["thread_id"], "deleted")
    assert client.post(path, json=body()).status_code == 404
    assert client.get(detail_path).json()["feedback"][0]["id"] == saved.id
    repo.catalog.purge(run["thread_id"])
    with repo.database.session() as session:
        assert session.scalar(select(func.count()).select_from(AnswerFeedback)) == 0


@pytest.mark.parametrize("content", ["字", "字" * 2000])
def test_optional_category_and_content_boundaries(feedback_client, content):
    client, repo, _, _, _, path = feedback_client
    response = client.post(path, json=body(content=content))
    assert response.status_code == 201, response.text
    with repo.database.session() as session:
        saved = session.get(AnswerFeedback, response.json()["id"])
        assert saved.content == content and saved.category == ""


@pytest.mark.parametrize(
    "extra",
    [
        {"content": ""},
        {"content": " \n\t"},
        {"content": "字" * 2001},
        {"content": None},
        {"content": 123},
        {"category": "unknown"},
        {"category": None},
        {"submission_id": "bad-id"},
        {"actor_id": "forged"},
        {"run_id": "forged"},
    ],
)
def test_invalid_feedback_does_not_write(feedback_client, extra):
    client, repo, _, _, _, path = feedback_client
    response = client.post(path, json=body(**extra))
    assert response.status_code == 422, response.text
    with repo.database.session() as session:
        assert session.scalar(select(func.count()).select_from(AnswerFeedback)) == 0


def test_feedback_authentication_scope_and_message_role(feedback_client):
    client, repo, _, run, answer, path = feedback_client
    assert client.post(path, json=body(), headers={"X-Arks-CSRF": "bad"}).status_code == 403
    question_path = path.replace(answer, run["message_id"])
    assert client.post(question_path, json=body()).status_code == 404
    assert client.post(path.replace(answer, "missing"), json=body()).status_code == 404
    wrong_scope = path.replace(path.split("/")[3], "independent")
    assert client.post(wrong_scope, json=body()).status_code == 404
    sign_in(client)
    client.post(
        "/api/admin/accounts",
        json={
            "username": "second",
            "display_name": "第二人",
            "password": "second-pass-123456",
        },
    )
    login = client.post(
        "/api/auth/login",
        json={
            "username": "second",
            "password": "second-pass-123456",
        },
    )
    client.headers["X-Arks-CSRF"] = login.json()["csrf_token"]
    assert client.post(path, json=body()).status_code == 404
    assert client.get(f"/api/admin/questions/{run['thread_id']}").status_code == 403
    client.cookies.clear()
    assert client.post(path, json=body()).status_code == 401
    with repo.database.session() as session:
        assert session.scalar(select(func.count()).select_from(AnswerFeedback)) == 0


def test_branch_answer_without_run_can_receive_feedback(feedback_client):
    client, repo, _, run, answer, path = feedback_client
    branch = repo.branches.fork(run["thread_id"], answer)
    copied = repo.thread(branch["id"])["messages"]
    copied_answer = next(item for item in copied if item["role"] == "assistant")
    copied_question = next(item for item in copied if item["role"] == "user")
    branch_path = path.replace(run["thread_id"], branch["id"]).replace(answer, copied_answer["id"])
    response = client.post(branch_path, json=body(category="other"))
    assert response.status_code == 201, response.text
    with repo.database.session() as session:
        saved = session.get(AnswerFeedback, response.json()["id"])
        assert saved.run_id is None
        assert saved.question_id == copied_question["id"]
        assert saved.message_id == copied_answer["id"]
        assert session.scalar(select(func.count()).select_from(Run)) == 1
