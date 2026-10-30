"""账号隔离必须覆盖目录、直接链接、读写、导出、队列和历史资料。"""

import io
import json
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth.context import request_identity
from app.modules.auth.models import Account
from app.modules.chat.models import Message
from app.modules.chat.runs import RunManager
from app.modules.projects.models import Project, ProjectMaterial, ProjectMaterialRevision
from app.modules.source_analysis.workspace import Workspace
from tests.helpers.accounts import login_second, sign_in
from tests.helpers.memories import MemorySeed, seed_memory

pytestmark = pytest.mark.authentication


def generated_memory(app, scope, user, content):
    token = request_identity.set({"user": user})
    try:
        seed_memory(
            app.state.projects.services(scope).memories,
            MemorySeed(name="后台记忆.md", content=content),
        )
    finally:
        request_identity.reset(token)


def create_project(client, name):
    forged = client.post("/api/projects", json={"name": name, "owner_id": "forged"})
    assert forged.status_code == 422 and "owner_id" in forged.json()["detail"]
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def create_answer(client, project_id, text):
    prefix = f"/api/p/{project_id}"
    response = client.post(prefix + "/threads/start", json={"content": text})
    assert response.status_code == 201, response.text
    run = response.json()
    client.app.state.projects.services(project_id).repository.finish(run["id"], "回答：" + text)
    return run


@pytest.fixture
def owned(services, monkeypatch):
    monkeypatch.setattr(RunManager, "start", lambda *_: None)
    app = create_app(services[0])
    with TestClient(app) as client:
        with app.state.auth.database.session.begin() as session:
            second = Account(
                username="second",
                display_name="第二人",
                role="user",
                password_hash=app.state.auth.hasher.hash("second-pass-123456"),
            )
            session.add(second)
        first_user = sign_in(client, "user").json()["user"]
        first = create_project(client, "甲的私有项目")
        run = create_answer(client, first["id"], "甲的私人问题")
        second_user = login_second(client)
        second = create_project(client, "乙的私有项目")
        yield client, app, first_user, second_user, first, second, run


def test_lists_search_pagination_and_account_ownership(owned):
    client, app, first_user, second_user, first, second, run = owned
    assert first["owner_id"] == first_user["id"] and second["owner_id"] == second_user["id"]
    listed = client.get("/api/projects").json()
    assert len(listed["projects"]) == 2
    assert second["id"] in {row["id"] for row in listed["projects"]}
    assert first["id"] not in {row["id"] for row in listed["projects"]}
    assert all(row["owner_id"] == second_user["id"] for row in listed["projects"])
    assert listed["default_project_id"] in {row["id"] for row in listed["projects"]}
    assert listed["projects"][0]["thread_count"] == 0
    assert client.get("/api/projects/search-threads?query=甲").json() == []
    assert client.get(f"/api/projects/thread-location/{run['thread_id']}").status_code == 404
    sign_in(client, "user")
    assert client.get("/api/projects/search-threads?query=甲").json()[0]["id"] == run["thread_id"]
    assert client.get(f"/api/p/{first['id']}/threads").json()[0]["owner_id"] == first_user["id"]
    assert (
        next(
            row
            for row in client.get("/api/projects").json()["projects"]
            if row["id"] == first["id"]
        )["thread_count"]
        == 1
    )
    sign_in(client, "admin")
    assert len(client.get("/api/projects").json()["projects"]) == 5
    assert client.get("/api/admin/questions").json()["total"] == 1
    assert client.get(f"/api/admin/questions/{run['thread_id']}").status_code == 200


def test_historical_regeneration_cannot_access_another_accounts_conversation(owned):
    client, app, _, _, first, _, original = owned
    repository = app.state.projects.services(first["id"]).repository
    later = repository.create_run(original["thread_id"], "后续私人问题", [])
    repository.finish(later["id"], "后续私人答案")
    before = repository.thread(original["thread_id"])
    response = client.post(f"/api/p/{first['id']}/runs/{original['id']}/regenerate")
    assert response.status_code == 404
    assert response.json()["detail"]
    assert repository.thread(original["thread_id"])["messages"] == before["messages"]


def test_other_account_cannot_read_write_export_or_reuse_cached_services(owned):
    client, app, _, _, first, second, run = owned
    project = f"/api/projects/{first['id']}"
    prefix = f"/api/p/{first['id']}"
    thread = f"{prefix}/threads/{run['thread_id']}"
    requests = [
        ("GET", project, None),
        ("PATCH", project, {"name": "越权"}),
        ("DELETE", project, None),
        ("POST", project + "/position", {"direction": 1}),
        ("GET", project + "/export", None),
        ("GET", prefix + "/threads", None),
        ("POST", prefix + "/threads", {}),
        ("GET", thread, None),
        ("GET", thread + "/export", None),
        ("GET", thread + "/context", None),
        ("PATCH", thread, {"title": "越权"}),
        ("DELETE", thread, None),
        ("POST", thread + "/restore", None),
        ("DELETE", thread + "/permanent", None),
        ("POST", thread + "/fork", {"message_id": run["message_id"]}),
        ("POST", thread + "/runs", {"content": "越权"}),
        ("GET", prefix + "/memories", None),
        ("GET", prefix + "/source-options", None),
        ("GET", prefix + "/file?path=Program.cs", None),
        ("GET", project + "/materials", None),
        ("GET", f"/api/projects/search-threads?project_id={first['id']}", None),
    ]
    for method, path, body in requests:
        response = client.request(method, path, json=body)
        assert response.status_code == 404, (method, path, response.text)
    for prefix in (f"/api/p/{first['id']}", f"/api/p/{second['id']}", "/api/p/independent", "/api"):
        for suffix in ("", "/context", "/trace", "/events", "/cancel", "/resume", "/regenerate"):
            method = "POST" if suffix in {"/cancel", "/resume", "/regenerate"} else "GET"
            response = client.request(method, f"{prefix}/runs/{run['id']}{suffix}")
            assert response.status_code == 404, response.text
    with app.state.auth.database.session() as session:
        assert session.get(Project, first["id"]).name == "甲的私有项目"


def test_independent_chats_memories_preferences_and_queue_are_private(owned):
    client, app, _, second_user, first, _, _ = owned
    prefix = "/api/p/independent"
    second_run = create_answer(client, "independent", "乙的独立对话")
    thread = prefix + f"/threads/{second_run['thread_id']}"
    assert client.post(thread + "/queue/pause").status_code == 200
    queue = client.post(thread + "/queue", json={"content": "乙的待发问题"}).json()["item"]
    memory = client.put(
        prefix + "/memories",
        json={"scope": "project", "name": "独立.md", "content": "乙的独立记忆"},
    )
    assert memory.status_code == 405, memory.text
    generated_memory(app, "independent", second_user, "乙的独立记忆")
    assert "乙的独立记忆" in client.get(prefix + "/memories").text
    preference = client.put(
        prefix + "/source-options", json={"version": 0, "source_options": {"use_memory": False}}
    )
    assert preference.status_code == 200, preference.text
    sign_in(client, "user")
    assert client.get(prefix + "/threads").json() == []
    assert client.get(prefix + "/source-options").json()["version"] == 0
    assert client.get(prefix + "/memories").json() == []
    assert client.get(prefix + "/memories/project/独立.md/history").status_code == 404
    assert (
        client.post(
            prefix + "/memories/project/独立.md/restore", json={"revision_id": 1}
        ).status_code
        == 404
    )
    for path in (thread, thread + "/queue"):
        assert client.get(path).status_code == 404
    assert client.delete(prefix + f"/queue/{queue['id']}").status_code == 404
    assert (
        client.patch(
            prefix + f"/queue/{queue['id']}",
            json={"content": "篡改", "version": queue["updated_at"]},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/projects/move-threads",
            json={"ids": [second_run["thread_id"]], "project_id": first["id"]},
        ).status_code
        == 404
    )
    login_second(client)
    assert client.get(thread).json()["owner_id"] == second_user["id"]
    assert client.get(thread + "/queue").json()["items"][0]["content"] == "乙的待发问题"
    branch = client.post(thread + "/fork", json={"message_id": second_run["message_id"]})
    assert branch.status_code == 201 and branch.json()["owner_id"] == second_user["id"]


def test_archive_trash_move_and_project_export_keep_ownership(owned):
    client, app, first_user, _, first, second, run = owned
    sign_in(client, "user")
    prefix = f"/api/p/{first['id']}"
    assert (
        client.patch(
            prefix + f"/threads/{run['thread_id']}", json={"state": "archived"}
        ).status_code
        == 200
    )
    assert len(client.get("/api/projects/search-threads?view=archived").json()) == 1
    exported = client.get(f"/api/projects/{first['id']}/export")
    assert exported.status_code == 200
    with ZipFile(io.BytesIO(exported.content)) as archive:
        saved = json.loads(archive.read(f"conversations/{run['thread_id']}.json"))
        assert (
            saved["owner_id"] == first_user["id"]
            and saved["messages"][0]["content"] == "甲的私人问题"
        )
    assert client.delete(f"/api/projects/{first['id']}?disposition=independent").status_code == 200
    thread = f"/api/p/independent/threads/{run['thread_id']}"
    assert client.get(thread).json()["owner_id"] == first_user["id"]
    assert client.delete(thread).status_code == 200
    login_second(client)
    assert client.get("/api/projects/search-threads?state=deleted").json() == []
    assert client.post(thread + "/restore").status_code == 404
    sign_in(client, "user")
    assert client.post(thread + "/restore").status_code == 200


def test_project_materials_memories_and_original_sources_cannot_cross_accounts(
    owned, services, tmp_path
):
    client, app, _, _, first, _, run = owned
    private_root = tmp_path / "private-source"
    private_root.mkdir()
    (private_root / "Program.cs").write_text("class PrivateSource {}", encoding="utf-8")
    private_source = Workspace(private_root)
    sign_in(client, "admin")
    assert (
        client.patch(
            f"/api/projects/{first['id']}", json={"source_root": str(private_root)}
        ).status_code
        == 200
    )
    sign_in(client, "user")
    prefix = f"/api/p/{first['id']}"
    assert client.get(prefix + "/file?path=Program.cs").status_code == 200
    with app.state.auth.database.session.begin() as session:
        session.get(Message, run["message_id"]).source_workspace_id = private_source.source_id
    source = f"/api/sources/{private_source.source_id}/file?path=Program.cs"
    assert client.get(source).status_code == 200
    with app.state.auth.database.session.begin() as session:
        material = ProjectMaterial(
            project_id=first["id"], title="旧私人资料", content="PRIVATE-MATERIAL"
        )
        session.add(material)
        session.flush()
        material_id = material.id
        session.add(
            ProjectMaterialRevision(
                material_id=material_id, version=1, title=material.title, content=material.content
            )
        )
    material_url = f"/api/projects/{first['id']}/materials/{material_id}?version=1"
    assert client.get(material_url).json()["content"] == "PRIVATE-MATERIAL"
    memory = client.put(
        prefix + "/memories",
        json={"scope": "project", "name": "项目.md", "content": "PRIVATE-PROJECT-MEMORY"},
    )
    assert memory.status_code == 405
    user = sign_in(client, "user").json()["user"]
    generated_memory(app, first["id"], user, "PRIVATE-PROJECT-MEMORY")
    assert "PRIVATE-PROJECT-MEMORY" in client.get(prefix + "/memories").text
    login_second(client)
    assert client.get(source).status_code == 404
    assert client.get(material_url).status_code == 404
    assert client.get(prefix + "/memories/project/项目.md/history").status_code == 404
    assert client.get("/api/memories").status_code == 404
    # 公司交接资料仍共享，与个人项目隔离是两个范围。
    source = client.post(
        "/api/handover/sources/text",
        json={"title": "共同资料", "content": "SHARED", "actor": "第二人"},
    )
    assert source.status_code == 201, source.text
    sign_in(client, "user")
    assert (
        client.get(f"/api/handover/records/{source.json()['id']}").json()["payload"]["content"]
        == "SHARED"
    )


def test_stale_browser_account_header_cannot_read_new_users_data(owned):
    client, _, first_user, _, _, _, _ = owned
    response = client.get("/api/projects", headers={"X-Arks-Account": first_user["id"]})
    assert response.status_code == 401
    assert "甲的私有项目" not in response.text and "乙的私有项目" not in response.text


def test_unowned_legacy_project_is_admin_only_and_restart_never_claims_it(services):
    app = create_app(services[0])
    for _ in range(2):
        with TestClient(app) as client:
            sign_in(client, "user")
            listed = client.get("/api/projects").json()
            assert len(listed["projects"]) == 1
            assert listed["default_project_id"] != services[2].id
            assert listed["projects"][0]["source_root"] == str(services[0].workspace)
            assert client.get(f"/api/projects/{services[2].id}").status_code == 404
            sign_in(client, "admin")
            assert (
                next(
                    row
                    for row in client.get("/api/projects").json()["projects"]
                    if row["id"] == services[2].id
                )["owner_id"]
                is None
            )
