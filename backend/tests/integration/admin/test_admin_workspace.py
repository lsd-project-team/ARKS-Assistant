"""管理员闭环：真实授权、账号撤权、问答归属和统计事实。"""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.modules.admin.models import BusinessSubmission, CollectionState, UsageActivity
from app.modules.auth.models import Account
from app.modules.chat.models import Message

pytestmark = pytest.mark.authentication


def login(client, name="admin", password=None):
    if password is None:
        initial = json.loads(client.app.state.auth.initial_accounts.read_text(encoding="utf-8"))
        password = next(row["password"] for row in initial if row["username"] == name)
    response = client.post("/api/auth/login", json={"username": name, "password": password})
    assert response.status_code == 200, response.text
    client.headers["X-Arks-CSRF"] = response.json()["csrf_token"]
    return response.json()["user"]


def test_admin_api_permissions_and_account_lifecycle(services):
    with TestClient(create_app(services[0])) as client:
        assert client.get("/api/admin/accounts").status_code == 401
        login(client, "user")
        assert client.get("/api/admin/accounts").status_code == 403
        assert client.get("/api/admin/overview").status_code == 403
        assert client.get("/api/admin/questions").status_code == 403
        admin = login(client)
        body = {
            "username": "engineer",
            "display_name": "工程师",
            "role": "user",
            "password": "testing-only-12345",
            "enabled": True,
        }
        created = client.post("/api/admin/accounts", json=body)
        assert created.status_code == 201, created.text
        identifier = created.json()["id"]
        assert "password" not in created.text
        assert client.post("/api/admin/accounts", json=body).status_code == 409
        assert (
            client.patch(
                f"/api/admin/accounts/{admin['id']}",
                json={"display_name": "管理员", "role": "user", "enabled": True},
            ).status_code
            == 409
        )
        users = client.get("/api/admin/accounts").json()
        assert len(users) == 3 and all("password_hash" not in row for row in users)
        login(client, "engineer", body["password"])
        login(client)
        updated = client.patch(
            f"/api/admin/accounts/{identifier}",
            json={"display_name": "工程师甲", "role": "user", "enabled": False},
        )
        assert updated.status_code == 200
        assert (
            client.post(
                "/api/auth/login", json={"username": "engineer", "password": body["password"]}
            ).status_code
            == 401
        )
        assert len(client.get("/api/admin/events").json()) == 2
        assert client.post(f"/api/admin/accounts/{identifier}/revoke").status_code == 200
        assert (
            client.patch(
                f"/api/admin/accounts/{identifier}",
                json={
                    "display_name": "工程师甲",
                    "role": "user",
                    "enabled": True,
                    "password": "new-testing-12345",
                },
            ).status_code
            == 200
        )
        login(client, "engineer", "new-testing-12345")


def test_visit_time_dedup_overlap_and_real_collection_start(services):
    with TestClient(create_app(services[0])) as client:
        user = login(client, "user")
        tracker = client.app.state.usage
        now = datetime.now(UTC)
        one = SimpleNamespace(visit_id=str(uuid4()), sequence=1, active_ms=15000)
        tracker.heartbeat(user, one, now)
        # 首次心跳无论客户端上报多少都不补时长。
        one.sequence = 2
        one.active_ms = 10000
        tracker.heartbeat(user, one, now + timedelta(seconds=10))
        tracker.heartbeat(user, one, now + timedelta(seconds=11))
        two = SimpleNamespace(visit_id=str(uuid4()), sequence=1, active_ms=0)
        tracker.heartbeat(user, two, now)
        two.sequence, two.active_ms = 2, 10000
        tracker.heartbeat(user, two, now + timedelta(seconds=10))
        with tracker.database.session() as session:
            assert sum(row.active_ms for row in session.scalars(select(UsageActivity))) == 10000
        one.sequence, one.active_ms = 3, 0  # 后台/失焦时没有有效时间。
        tracker.heartbeat(user, one, now + timedelta(seconds=20))
        login(client)
        overview = client.get("/api/admin/overview?period=all").json()
        assert overview["visits"] == 2
        assert overview["active_users"] == 1
        assert overview["active_ms"] == 10000
        assert overview["tasks"] == 0
        assert overview["collected_since"]
        assert client.get("/api/admin/overview?period=90").status_code == 422
        assert client.post(
            "/api/usage/heartbeat", json={"visit_id": str(uuid4()), "sequence": 1, "active_ms": 0}
        ).json() == {"collected": False}


def test_successful_business_submissions_range_and_stock(services):
    with TestClient(create_app(services[0])) as client:
        user = login(client, "user")
        for _ in range(2):
            saved = client.post(
                "/api/handover/sources/text",
                headers={"X-Arks-Submission-ID": "same-operation"},
                json={"title": "资料", "content": "实际业务正文", "actor": "整理人"},
            )
            assert saved.status_code == 201, saved.text
        assert client.post("/api/handover/sources/text", json={"title": ""}).status_code == 422
        login(client)
        all_time = client.get("/api/admin/overview?period=all").json()
        assert all_time["tasks"] == 1
        with services[1].session.begin() as session:
            session.get(CollectionState, "default").started_at = (
                datetime.now(UTC) - timedelta(days=50)
            ).isoformat()
            session.add(
                BusinessSubmission(
                    id="older-submit",
                    account_id=user["id"],
                    category="交接业务",
                    created_at=(datetime.now(UTC) - timedelta(days=20)).isoformat(),
                )
            )
        week = client.get("/api/admin/overview?period=7").json()
        month = client.get("/api/admin/overview?period=30").json()
        assert week["tasks"] == 1 and month["tasks"] == 2
        assert week["data_total"] == month["data_total"]
        assert week["data_breakdown"]["交接记录"] == 2
        assert week["data_total"] == sum(week["data_breakdown"].values())


def test_question_ownership_queue_history_versions_and_readonly_admin(services, monkeypatch):
    with TestClient(create_app(services[0])) as client:
        user = login(client, "user")
        project = client.post("/api/projects", json={"name": "用户的项目"}).json()["id"]
        project_services = client.app.state.projects.services(project)
        repo = project_services.repository
        # 真实 HTTP 问题走项目分派和请求身份，仅替换外部供应商执行。
        monkeypatch.setattr(project_services.runs, "start", lambda run: None)
        response = client.post(
            f"/api/p/{project}/threads/start", json={"content": "分析测试函数", "selections": []}
        )
        assert response.status_code == 201, response.text
        run = response.json()
        queued_response = client.post(
            f"/api/p/{project}/threads/{run['thread_id']}/queue",
            json={"content": "后续问题", "selections": []},
        )
        assert queued_response.status_code == 201, queued_response.text
        queued = queued_response.json()["item"]
        repo.finish(run["id"], "实际回答内容")
        repo.finish(run["id"], "不能重复落库")
        # 后台出队时没有 HTTP 身份，仍必须保留排队者。
        dispatched = repo.queue.dispatch(run["thread_id"])
        assert dispatched
        assert repo.message(dispatched["message_id"])["actor_id"] == user["id"]
        repo.finish(dispatched["id"], "后续回答")
        regenerated = repo.regenerate(dispatched["id"])
        repo.finish(regenerated["id"], "重新生成的回答")
        old = repo.create_run(None, "历史未知身份", [])
        repo.finish(old["id"], "旧的回答")
        login(client)
        listing = client.get(f"/api/admin/questions?user_id={user['id']}&status=completed").json()
        assert listing["total"] == 1
        assert listing["items"][0]["questions"] == 2
        detail = client.get(f"/api/admin/questions/{run['thread_id']}").json()
        assert len(detail["messages"]) == 5 and len(detail["runs"]) == 3
        assert detail["messages"][0]["actor"]["username"] == "user"
        assert (
            len(client.get(f"/api/admin/questions/{run['thread_id']}?limit=2").json()["messages"])
            == 2
        )
        assert client.get("/api/admin/questions?user_id=unknown").json()["total"] == 1
        assert client.get("/api/admin/questions?query=重新生成").json()["total"] == 1
        # 本轮另有一次普通用户创建私有项目的业务提交。
        assert client.get("/api/admin/overview?period=all").json()["tasks"] == 3
        assert client.get("/api/admin/questions?query=%25").json()["total"] == 0
        assert client.get(f"/api/admin/questions?project_id={project}").json()["total"] == 2
        assert queued["actor_id"] == user["id"]
        with services[1].session() as session:
            assert (
                session.scalar(select(Message).where(Message.id == old["message_id"])).actor_id
                is None
            )
            assert session.scalar(select(Account).where(Account.id == user["id"])).enabled
