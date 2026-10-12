"""项目迁移、跨项目隔离及移动后的引用来源。"""

import asyncio
import threading
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Thread
from app.project_context import bind_project, project_prompt


def create_project(client, name, root=None, instructions=""):
    response = client.post(
        "/api/projects", json={"name": name, "source_root": root, "instructions": instructions}
    )
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
        first = create_project(client, "A", str(paths.workspace), "简短回答")
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
            == 200
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


def test_archive_remove_and_running_guard(services):
    paths = services[0]
    app = create_app(paths)
    with TestClient(app) as client:
        project = create_project(client, "可归档", str(paths.workspace))
        repository = app.state.projects.services(project["id"]).repository
        run = repository.create_run(None, "问题", [])
        assert (
            client.patch(f"/api/projects/{project['id']}", json={"state": "archived"}).status_code
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
            == 200
        )
        assert client.get(scoped(project, f"/threads/{run['thread_id']}")).status_code == 200
        assert client.post(scoped(project, "/threads"), json={}).status_code == 409
        assert (
            client.patch(f"/api/projects/{project['id']}", json={"state": "active"}).status_code
            == 200
        )
        assert (
            client.delete(f"/api/projects/{project['id']}?disposition=independent").status_code
            == 200
        )
        assert paths.workspace.is_dir()
        assert client.get(f"/api/p/independent/threads/{run['thread_id']}").status_code == 200


def test_instruction_snapshot_is_task_local():
    with bind_project({"name": "项目 A", "instructions": "先核对源码"}):
        assert "项目 A" in project_prompt()
        assert "先核对源码" in project_prompt()
    assert project_prompt() == ""


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


def test_sidebar_recent_filters_archived_projects_before_pagination_and_trash_keeps_them(services):
    with TestClient(create_app(services[0])) as client:
        active = create_project(client, "正常项目")
        archived = create_project(client, "归档项目")
        normal = client.post(scoped(active, "/threads"), json={"title": "正常对话"}).json()
        independent = client.post("/api/p/independent/threads", json={"title": "独立对话"}).json()
        hidden = [
            client.post(
                scoped(archived, "/threads"), json={"title": f"归档中的对话 {index}"}
            ).json()
            for index in range(6)
        ]
        assert (
            client.patch(f"/api/projects/{archived['id']}", json={"state": "archived"}).status_code
            == 200
        )
        response = client.get(
            "/api/projects/search-threads?state=active&project_state=active&limit=2"
        )
        assert response.status_code == 200
        assert {row["id"] for row in response.json()} == {normal["id"], independent["id"]}
        assert (
            client.get(
                "/api/projects/search-threads?state=active&offset=1&limit=1&project_state=active"
            ).json()[0]["id"]
            == normal["id"]
        )
        unfiltered = client.get("/api/projects/search-threads?state=active").json()
        assert len(unfiltered) == 8
        assert unfiltered[0]["project_state"] == "archived"
        assert client.delete(scoped(archived, f"/threads/{hidden[0]['id']}")).status_code == 200
        trash = client.get("/api/projects/search-threads?state=deleted").json()
        assert [row["id"] for row in trash] == [hidden[0]["id"]]
        assert (
            client.post(scoped(archived, f"/threads/{hidden[0]['id']}/restore")).status_code == 200
        )
        assert client.get("/api/projects/search-threads?state=deleted").json() == []
        assert client.get("/api/projects/search-threads?project_state=invalid").status_code == 422


def test_search_views_filter_status_and_project_before_pagination(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        active = create_project(client, "正常项目")
        archived = create_project(client, "归档项目")
        client.patch(f"/api/projects/{archived['id']}", json={"state": "archived"})
        combinations = [
            (active["id"], "active"),
            (active["id"], "archived"),
            (archived["id"], "active"),
            (archived["id"], "archived"),
            (active["id"], "deleted"),
            (archived["id"], "deleted"),
            (None, "active"),
            (None, "archived"),
            (None, "deleted"),
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

        def expected(view, project_id="all"):
            return [
                row["id"]
                for row in reversed(records)
                if (project_id == "all" or row["project_id"] == project_id)
                and (
                    row["state"] == view
                    or (
                        view == "archived"
                        and row["state"] == "active"
                        and row["project_id"] == archived["id"]
                    )
                )
            ]

        for view in ("archived", "deleted"):
            rows = []
            for offset in range(0, len(expected(view)) + 7, 7):
                response = client.get(
                    f"/api/projects/search-threads?view={view}&query=共同关键词&limit=7&offset={offset}"
                )
                assert response.status_code == 200
                rows.extend(response.json())
            assert [row["id"] for row in rows] == expected(view)
            for project_id in (active["id"], archived["id"], "independent"):
                result = client.get(
                    f"/api/projects/search-threads?view={view}&project_id={project_id}&limit=200"
                ).json()
                assert [row["id"] for row in result] == expected(
                    view, None if project_id == "independent" else project_id
                )
            assert (
                client.get(f"/api/projects/search-threads?view={view}&query=不存在的关键词").json()
                == []
            )
        archived_projects = client.get(
            "/api/projects/search-threads?state=active&project_state=archived"
        ).json()
        assert all(row["project_id"] == archived["id"] for row in archived_projects)
        assert client.get("/api/projects/search-threads?view=invalid").status_code == 422
        assert (
            client.get("/api/projects/search-threads?view=archived&project_id=missing").status_code
            == 404
        )


def test_project_order_pinning_and_archive_queue_guard(services):
    with TestClient(create_app(services[0])) as client:
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
        client.patch(f"/api/projects/{first['id']}", json={"state": "archived"})
        assert (
            client.post(
                scoped(first, f"/threads/{thread['id']}/queue"), json={"content": "不应加入队列"}
            ).status_code
            == 409
        )


def test_running_projects_keep_instruction_and_source_snapshots(services, tmp_path, monkeypatch):
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

    monkeypatch.setattr("app.runtime.AgentRuntime.execute", execute)
    app = create_app(services[0])
    with TestClient(app) as client:
        first = create_project(client, "项目 A", str(services[0].workspace), "A 的旧指令")
        second = create_project(client, "项目 B", str(other), "B 的指令")
        try:
            run_a = client.post(scoped(first, "/threads/start"), json={"content": "问题 A"}).json()
            run_b = client.post(scoped(second, "/threads/start"), json={"content": "问题 B"}).json()
            assert all(event.wait(3) for event in started.values())
            assert (
                client.patch(
                    f"/api/projects/{first['id']}", json={"instructions": "A 的新指令"}
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
            assert "A 的旧指令" in seen["项目 A"][0] and "A 的新指令" not in seen["项目 A"][0]
            assert seen["项目 A"][1].startswith("class Program")
            assert "B 的指令" in seen["项目 B"][0] and seen["项目 B"][1] == "source B"
            assert client.get(scoped(first, f"/runs/{run_a['id']}")).json()["status"] == "completed"
            assert (
                client.get(scoped(second, f"/runs/{run_b['id']}")).json()["status"] == "completed"
            )
        finally:
            release.set()
