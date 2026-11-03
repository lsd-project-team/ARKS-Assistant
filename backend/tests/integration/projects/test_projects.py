"""项目迁移、跨项目隔离及移动后的引用来源。"""

import asyncio
import threading
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.chat.models import Thread
from app.modules.projects.context import bind_project, project_prompt


def create_project(client, name, root=None):
    response = client.post("/api/projects", json={"name": name, "source_root": root})
    assert response.status_code == 201, response.text
    return response.json()


def scoped(project, path):
    return f"/api/p/{project['id']}{path}"


def test_legacy_adoption_and_restart_preserves_identity(services):
    paths, database, workspace, repository, *_ = services
    thread = repository.create_thread("原有对话")
    run = repository.create_run(thread["id"], "入口函数", [])
    repository.finish(run["id"], "原有答案")
    with TestClient(create_app(paths)) as client:
        response = client.get("/api/projects").json()
        project = response["projects"][0]
        assert project["id"] == workspace.id
        saved = client.get(scoped(project, f"/threads/{thread['id']}")).json()
        assert saved["project_id"] == project["id"]
        assert [row["content"] for row in saved["messages"]] == ["入口函数", "原有答案"]
        assert all(row["source_workspace_id"] == workspace.id for row in saved["messages"])
        renamed = client.patch(f"/api/projects/{project['id']}", json={"name": "重新命名"})
        assert renamed.status_code == 200
    with TestClient(create_app(paths)) as client:
        assert client.get("/api/projects").json()["projects"][0]["name"] == "重新命名"
        assert client.get(scoped(project, f"/threads/{thread['id']}")).status_code == 200


def test_project_isolation_same_source_and_empty_project(services):
    paths = services[0]
    with TestClient(create_app(paths)) as client:
        first = create_project(client, "A", str(paths.workspace))
        second = create_project(client, "B", str(paths.workspace))
        empty = create_project(client, "空项目")
        thread = client.post(scoped(first, "/threads"), json={}).json()
        assert client.get(scoped(second, f"/threads/{thread['id']}")).status_code == 404
        assert client.get(scoped(first, "/threads")).json()[0]["project_id"] == first["id"]
        assert client.get(scoped(second, "/threads")).json() == []
        assert client.get(scoped(empty, "/files")).json() == []
        assert client.get(scoped(empty, "/file?path=Program.cs")).status_code == 404
        assert (
            client.put(
                scoped(first, "/memories"),
                json={"name": "项目.md", "scope": "project", "content": "项目 A 的约定"},
            ).status_code
            == 405
        )
        assert client.get(scoped(second, "/memories")).json() == []
        assert client.get(scoped(first, "/file?path=Program.cs")).status_code == 200
        assert client.get(scoped(first, "/file?path=../secret")).status_code == 409


def test_move_keeps_source_identity_and_all_messages(services, tmp_path):
    paths = services[0]
    other = tmp_path / "other"
    other.mkdir()
    (other / "Program.cs").write_text("other source", encoding="utf-8")
    app = create_app(paths)
    with TestClient(app) as client:
        first = create_project(client, "A", str(paths.workspace))
        second = create_project(client, "B", str(other))
        repository = app.state.projects.services(first["id"]).repository
        run = repository.create_run(None, "问题", [])
        repository.finish(run["id"], "[引用](source:Program.cs#L1)")
        moved = client.post(
            "/api/projects/move-threads",
            json={"ids": [run["thread_id"]], "project_id": second["id"]},
        )
        assert moved.status_code == 200
        assert client.get(scoped(first, f"/threads/{run['thread_id']}")).status_code == 404
        thread = client.get(scoped(second, f"/threads/{run['thread_id']}")).json()
        assert thread["project_id"] == second["id"]
        assert len(thread["messages"]) == 2
        assert thread["context_generation"] == 1
        source_id = thread["messages"][1]["source_workspace_id"]
        assert (
            client.get(f"/api/sources/{source_id}/file?path=Program.cs")
            .json()["content"]
            .startswith("class Program")
        )
        assert (
            client.get(scoped(second, "/file?path=Program.cs")).json()["content"] == "other source"
        )
        assert (
            client.post(
                "/api/projects/move-threads", json={"ids": [run["thread_id"]], "project_id": None}
            ).status_code
            == 200
        )
        assert (
            client.get(f"/api/p/independent/threads/{run['thread_id']}").json()["project_id"]
            is None
        )


def test_remove_move_and_source_change_keep_running_guard(services, tmp_path):
    paths = services[0]
    other = tmp_path / "other-source"
    other.mkdir()
    app = create_app(paths)
    with TestClient(app) as client:
        project = create_project(client, "运行保护", str(paths.workspace))
        repository = app.state.projects.services(project["id"]).repository
        run = repository.create_run(None, "问题", [])
        assert client.delete(f"/api/projects/{project['id']}").status_code == 409
        assert (
            client.patch(
                f"/api/projects/{project['id']}", json={"source_root": str(other)}
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/projects/move-threads", json={"ids": [run["thread_id"]], "project_id": None}
            ).status_code
            == 409
        )
        repository.finish(run["id"], "结果")
        assert (
            client.patch(f"/api/projects/{project['id']}", json={"state": "archived"}).status_code
            == 422
        )
        assert client.get(scoped(project, f"/threads/{run['thread_id']}")).status_code == 200
        assert client.post(scoped(project, "/threads"), json={}).status_code == 201
        assert (
            client.delete(f"/api/projects/{project['id']}?disposition=independent").status_code
            == 200
        )
        assert paths.workspace.is_dir()
        assert client.get(f"/api/p/independent/threads/{run['thread_id']}").status_code == 200


def test_project_name_is_task_local_and_retired_fields_are_ignored():
    with bind_project({"name": "项目 A", "instructions": "旧指令", "description": "旧说明"}):
        assert project_prompt() == "\n当前项目：项目 A\n"
    assert project_prompt() == ""


@pytest.mark.parametrize("field", ["description", "instructions"])
def test_retired_project_settings_are_rejected_and_not_returned(services, field):
    with TestClient(create_app(services[0])) as client:
        project = create_project(client, "保留名称", str(services[0].workspace))
        for body, path, method in (
            ({"name": "不应创建", field: "旧设置"}, "/api/projects", client.post),
            ({"name": "不应改名", field: "旧设置"}, f"/api/projects/{project['id']}", client.patch),
        ):
            response = method(path, json=body)
            assert response.status_code == 422
            assert f"body.{field}:" in response.json()["detail"]
        response = client.get(f"/api/projects/{project['id']}")
        assert response.status_code == 200 and response.json()["name"] == "保留名称"
        assert field not in response.json()
        assert field not in project
        assert all(
            row["name"] != "不应创建" for row in client.get("/api/projects").json()["projects"]
        )
        assert field not in client.app.state.projects.snapshot(project["id"])
        assert field not in client.app.state.projects.snapshot("independent")


def test_removed_default_project_does_not_break_restart(services):
    paths = services[0]
    with TestClient(create_app(paths)) as client:
        project = client.get("/api/projects").json()["projects"][0]
        thread = client.post(scoped(project, "/threads"), json={}).json()
        assert (
            client.delete(f"/api/projects/{project['id']}?disposition=independent").status_code
            == 200
        )
    with TestClient(create_app(paths)) as client:
        assert client.get("/api/projects").json()["projects"] == []
        assert client.get(f"/api/p/independent/threads/{thread['id']}").status_code == 200
        assert client.get(f"/api/projects/{project['id']}").status_code == 404


@pytest.mark.parametrize("disposition", ["independent", "trash"])
def test_remove_project_preserves_messages_citations_and_source_files(services, disposition):
    paths = services[0]
    with TestClient(create_app(paths)) as client:
        project = create_project(client, "删除流程", str(paths.workspace))
        repository = client.app.state.projects.services(project["id"]).repository
        run = repository.create_run(None, "保留原问题", [{"path": "Program.cs"}])
        repository.finish(run["id"], "保留原回答")
        thread_id = run["thread_id"]
        original = repository.thread(thread_id)
        source = (paths.workspace / "Program.cs").read_bytes()
        old_deleted = repository.create_thread("原回收站对话")
        repository.catalog.change(old_deleted["id"], "deleted")
        response = client.delete(f"/api/projects/{project['id']}?disposition={disposition}")
        assert response.status_code == 200 and response.json()["thread_count"] == 2
        assert client.get(f"/api/projects/{project['id']}").status_code == 404
        assert (paths.workspace / "Program.cs").read_bytes() == source
        current = client.app.state.projects.services("independent").repository
        saved = current.catalog.get(thread_id, include_deleted=True)
        assert saved["project_id"] is None and saved["workspace_id"] == "independent"
        assert saved["state"] == ("deleted" if disposition == "trash" else "active")
        assert current.catalog.get(old_deleted["id"], include_deleted=True)["state"] == "deleted"
        if disposition == "trash":
            assert client.post(f"/api/p/independent/threads/{thread_id}/restore").status_code == 200
        reloaded = current.thread(thread_id)
        assert reloaded["messages"] == original["messages"]
        assert reloaded["runs"] == original["runs"]


def test_source_change_restarts_context_and_preserves_original_citations(services, tmp_path):
    paths = services[0]
    other = tmp_path / "different"
    other.mkdir()
    (other / "Program.cs").write_text("new root", encoding="utf-8")
    app = create_app(paths)
    with TestClient(app) as client:
        project = create_project(client, "换目录", str(paths.workspace))
        repo = app.state.projects.services(project["id"]).repository
        run = repo.create_run(None, "旧问题", [])
        repo.finish(run["id"], "旧答案")
        old_source = client.get(f"/api/projects/{project['id']}").json()["source_workspace_id"]
        assert (
            client.patch(
                f"/api/projects/{project['id']}", json={"source_root": str(other)}
            ).status_code
            == 200
        )
        assert client.get(scoped(project, "/file?path=Program.cs")).json()["content"] == "new root"
        thread = client.get(scoped(project, f"/threads/{run['thread_id']}")).json()
        assert thread["context_generation"] == 1
        assert thread["messages"][1]["source_workspace_id"] == old_source
        assert client.post(scoped(project, f"/runs/{run['id']}/regenerate")).status_code == 409
    with TestClient(create_app(paths)) as client:
        assert client.get(scoped(project, "/file?path=Program.cs")).json()["content"] == "new root"
        assert (
            client.get(f"/api/sources/{old_source}/file?path=Program.cs")
            .json()["content"]
            .startswith("class Program")
        )


def test_global_search_paginates_beyond_two_hundred_and_shows_project(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        first, second = create_project(client, "检索 A"), create_project(client, "检索 B")
        with app.state.projects.database.session.begin() as session:
            for index in range(240):
                project = first if index < 220 else second
                stamp = (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=index)).isoformat()
                session.add(
                    Thread(
                        id=f"search-{index}",
                        project_id=project["id"],
                        workspace_id=project["id"],
                        title=f"检索 {index}",
                        created_at=stamp,
                        updated_at=stamp,
                    )
                )
        rows = []
        for offset in range(0, 250, 50):
            response = client.get(
                f"/api/projects/search-threads?query=检索&limit=50&offset={offset}"
            )
            assert response.status_code == 200
            rows.extend(response.json())
        assert [row["id"] for row in rows] == [f"search-{index}" for index in range(239, -1, -1)]
        assert rows[0]["project_name"] == "检索 B" and rows[-1]["project_name"] == "检索 A"


def test_sidebar_recent_paginates_all_projects_and_trash_keeps_ownership(services):
    with TestClient(create_app(services[0])) as client:
        first = create_project(client, "项目 A")
        second = create_project(client, "项目 B")
        normal = client.post(scoped(first, "/threads"), json={"title": "正常对话"}).json()
        independent = client.post("/api/p/independent/threads", json={"title": "独立对话"}).json()
        recent = [
            client.post(scoped(second, "/threads"), json={"title": f"最近对话 {i}"}).json()
            for i in range(6)
        ]
        rows = client.get("/api/projects/search-threads?state=active").json()
        assert {row["id"] for row in rows} == {
            normal["id"],
            independent["id"],
            *(row["id"] for row in recent),
        }
        assert [
            row["id"]
            for row in client.get(
                "/api/projects/search-threads?state=active&offset=1&limit=2"
            ).json()
        ] == [row["id"] for row in rows[1:3]]
        assert client.delete(scoped(second, f"/threads/{recent[0]['id']}")).status_code == 200
        trash = client.get("/api/projects/search-threads?state=deleted").json()
        assert [row["id"] for row in trash] == [recent[0]["id"]]
        assert trash[0]["project_id"] == second["id"]
        assert client.post(scoped(second, f"/threads/{recent[0]['id']}/restore")).status_code == 200
        assert client.get("/api/projects/search-threads?state=deleted").json() == []


def test_search_filters_status_and_project_before_pagination(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        first = create_project(client, "项目 A")
        second = create_project(client, "项目 B")
        combinations = [
            (project_id, state)
            for project_id in (first["id"], second["id"], None)
            for state in ("active", "deleted")
        ]
        records = []
        with app.state.projects.database.session.begin() as session:
            for index in range(135):
                project_id, state = combinations[index % len(combinations)]
                stamp = (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=index)).isoformat()
                identifier = f"view-search-{index}"
                session.add(
                    Thread(
                        id=identifier,
                        project_id=project_id,
                        workspace_id=project_id or "independent",
                        state=state,
                        title="共同关键词",
                        created_at=stamp,
                        updated_at=stamp,
                    )
                )
                records.append({"id": identifier, "project_id": project_id, "state": state})

        def expected(state, project_id="all"):
            return [
                row["id"]
                for row in reversed(records)
                if (project_id == "all" or row["project_id"] == project_id)
                and row["state"] == state
            ]

        for state in ("active", "deleted"):
            rows = []
            for offset in range(0, len(expected(state)) + 7, 7):
                response = client.get(
                    f"/api/projects/search-threads?state={state}&query=共同关键词&limit=7&offset={offset}"
                )
                assert response.status_code == 200
                rows.extend(response.json())
            assert [row["id"] for row in rows] == expected(state)
            for project_id in (first["id"], second["id"], "independent"):
                scope = "view=deleted" if state == "deleted" else "state=active"
                result = client.get(
                    f"/api/projects/search-threads?{scope}&project_id={project_id}&limit=200"
                ).json()
                assert [row["id"] for row in result] == expected(
                    state, None if project_id == "independent" else project_id
                )
            assert (
                client.get(
                    f"/api/projects/search-threads?state={state}&query=不存在的关键词"
                ).json()
                == []
            )
        for query in ("view=invalid", "view=archived", "state=archived"):
            assert client.get(f"/api/projects/search-threads?{query}").status_code == 422
        assert (
            client.get("/api/projects/search-threads?view=deleted&project_id=missing").status_code
            == 404
        )
        assert client.get("/api/projects?state=archived").status_code == 422


def test_project_order_pinning_and_remove_queue_guard(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        first, second = create_project(client, "排序 A"), create_project(client, "排序 B")
        assert (
            client.post(
                f"/api/projects/{second['id']}/position", json={"direction": -1}
            ).status_code
            == 200
        )
        rows = client.get("/api/projects").json()["projects"]
        assert [item["name"] for item in rows][-2:] == ["排序 B", "排序 A"]
        client.patch(f"/api/projects/{first['id']}", json={"pinned": True})
        assert client.get("/api/projects").json()["projects"][0]["id"] == first["id"]
        thread = client.post(scoped(first, "/threads"), json={}).json()
        repository = app.state.projects.services(first["id"]).repository
        queued = repository.queue.add(thread["id"], "仍在等待的问题", [])
        assert client.delete(f"/api/projects/{first['id']}").status_code == 409
        assert repository.queue.list(thread["id"])["items"][0]["id"] == queued["id"]


def test_running_projects_keep_name_and_source_snapshots(services, tmp_path, monkeypatch):
    other = tmp_path / "run-b"
    other.mkdir()
    (other / "Program.cs").write_text("source B", encoding="utf-8")
    release = threading.Event()
    started = {"项目 A": threading.Event(), "项目 B": threading.Event()}
    seen = {}

    async def execute(runtime, run, _emit):
        name = run["project_snapshot"]["name"]
        started[name].set()
        await asyncio.to_thread(release.wait, 10)
        seen[name] = (project_prompt(), runtime.workspace.read("Program.cs")["content"])
        return name

    monkeypatch.setattr("app.agents.runtime.engine.AgentRuntime.execute", execute)
    app = create_app(services[0])
    with TestClient(app) as client:
        first = create_project(client, "项目 A", str(services[0].workspace))
        second = create_project(client, "项目 B", str(other))
        try:
            run_a = client.post(scoped(first, "/threads/start"), json={"content": "问题 A"}).json()
            run_b = client.post(scoped(second, "/threads/start"), json={"content": "问题 B"}).json()
            assert all(event.wait(3) for event in started.values())
            assert (
                client.patch(
                    f"/api/projects/{first['id']}", json={"name": "项目 A 新名称"}
                ).status_code
                == 200
            )
            release.set()

            async def finish_tasks():
                tasks = [
                    *app.state.projects.services(first["id"]).runs.tasks.values(),
                    *app.state.projects.services(second["id"]).runs.tasks.values(),
                ]
                await asyncio.wait_for(asyncio.gather(*tasks), 3)

            client.portal.call(finish_tasks)
            assert seen["项目 A"][0] == "\n当前项目：项目 A\n"
            assert seen["项目 A"][1].startswith("class Program")
            assert seen["项目 B"] == ("\n当前项目：项目 B\n", "source B")
            snapshot = client.get(scoped(first, f"/runs/{run_a['id']}")).json()["project_snapshot"]
            assert "description" not in snapshot and "instructions" not in snapshot
            assert client.get(scoped(first, f"/runs/{run_a['id']}")).json()["status"] == "completed"
            assert (
                client.get(scoped(second, f"/runs/{run_b['id']}")).json()["status"] == "completed"
            )
        finally:
            release.set()
