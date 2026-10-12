"""项目资料的隔离、版本引用、确认入口、导出和多源码目录。"""

import io
import json
import zipfile

from fastapi.testclient import TestClient

from app.main import create_app
from app.project_materials import MaterialCorpus
from app.source_backend import SourceBackend
from app.source_evidence import SourceEvidence, source_excerpt


async def test_runtime_materials_toggle_and_fixed_tool_versions(services, monkeypatch):
    app = create_app(services[0])
    monkeypatch.setattr("app.runtime.create_deep_agent", lambda **kwargs: kwargs)
    with TestClient(app) as client:
        first, second = project(client, "资料项目 A"), project(client, "资料项目 B")
        original = client.post(
            materials(first), json={"title": "报警约定", "content": "报警处理：先确认轴停止。"}
        ).json()
        client.post(
            materials(second), json={"title": "报警约定", "content": "B 项目的私有处理约定。"}
        )
        runtime = app.state.projects.services(first["id"]).runtime
        enabled = await runtime.graph(
            "material-test",
            None,
            lambda *_: None,
            inspection=True,
            memory_query="报警处理",
            source_options={"use_knowledge": True},
        )
        assert "先确认轴停止" in enabled["system_prompt"]
        assert "B 项目的私有" not in enabled["system_prompt"]
        assert "search_project_materials" in {item.name for item in enabled["tools"]}
        client.patch(
            materials(first) + "/" + original["id"],
            json={"content": "新的报警处理版本。", "version": 1},
        )
        reader = next(item for item in enabled["tools"] if item.name == "read_project_material")
        old = json.loads(await reader.ainvoke({"material_id": original["id"]}))
        assert old["version"] == 1 and "先确认轴停止" in old["content"]
        disabled = await runtime.graph(
            "material-test-off",
            None,
            lambda *_: None,
            inspection=True,
            memory_query="报警处理",
            source_options={"use_knowledge": False},
        )
        assert "新的报警处理版本" not in disabled["system_prompt"]
        assert "read_project_material" not in {item.name for item in disabled["tools"]}


def project(client, name, root=None, folders=None):
    return client.post(
        "/api/projects", json={"name": name, "source_root": root, "source_folders": folders or []}
    ).json()


def materials(project):
    return f"/api/projects/{project['id']}/materials"


def test_material_isolation_versions_and_archive_guard(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        first, second = project(client, "A"), project(client, "B")
        original = client.post(
            materials(first),
            json={"title": "报警说明", "content": "报警处理约定\n先停止运动，再复位。"},
        ).json()
        corpus = MaterialCorpus(app.state.projects.database, first["id"])
        assert corpus.search("报警处理")[0]["version"] == 1
        assert MaterialCorpus(app.state.projects.database, second["id"]).search("报警") == []
        url = materials(first) + "/" + original["id"]
        assert client.get(materials(second) + "/" + original["id"]).status_code == 404
        edited = client.patch(
            url, json={"title": "新版报警说明", "content": "先确认轴停止再复位。", "version": 1}
        )
        assert edited.status_code == 200
        assert client.patch(url, json={"content": "冲突内容", "version": 1}).status_code == 409
        assert corpus.excerpt(original["id"])["content"].endswith("先停止运动，再复位。")
        historical = client.get(url + "?version=1").json()
        assert historical["title"] == "报警说明"
        assert client.patch(url, json={"state": "deleted", "version": 2}).status_code == 200
        assert client.get(url).status_code == 404
        assert client.get(url + "?version=1").status_code == 200
        assert not MaterialCorpus(app.state.projects.database, first["id"]).search("复位")
        assert client.patch(url, json={"state": "active", "version": 3}).status_code == 200
        assert (
            client.patch(f"/api/projects/{first['id']}", json={"state": "archived"}).status_code
            == 200
        )
        assert (
            client.post(materials(first), json={"title": "新资料", "content": "正文"}).status_code
            == 409
        )
        assert client.patch(url, json={"content": "更改", "version": 4}).status_code == 409
        assert client.get(url).status_code == 200


def test_conclusion_source_validation_and_project_export(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        first, second = project(client, "A"), project(client, "B")
        repo = app.state.projects.services(first["id"]).repository
        run = repo.create_run(None, "问题", [])
        repo.finish(run["id"], "有待核对的回复")
        conversation = repo.thread(run["thread_id"])
        answer = conversation["messages"][-1]
        body = {
            "title": "用户整理的结论",
            "content": "报警时先停机。",
            "kind": "conclusion",
            "origin_message_id": answer["id"],
        }
        assert client.post(materials(second), json=body).status_code == 409
        assert (
            client.post(
                materials(first), json={**body, "origin_message_id": run["message_id"]}
            ).status_code
            == 409
        )
        saved = client.post(materials(first), json=body)
        assert saved.status_code == 201
        assert saved.json()["origin_thread_id"] == run["thread_id"]
        corpus = MaterialCorpus(app.state.projects.database, first["id"])
        prompt, included = corpus.prompt("报警", 1000)
        assert "报警时先停机。" in prompt and "用户确认" in prompt
        assert included[0]["citation"].startswith("material:" + first["id"])
        other_repo = app.state.projects.services(second["id"]).repository
        other_repo.create_thread("B 的私有对话")
        downloaded = client.get(f"/api/projects/{first['id']}/export")
        assert downloaded.status_code == 200
        with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
            data = json.loads(archive.read(f"conversations/{run['thread_id']}.json"))
            assert data["messages"][-1]["content"] == answer["content"]
            material = json.loads(archive.read(f"materials/{saved.json()['id']}.json"))
            assert material["revisions"][0]["version"] == 1
            assert (
                len([name for name in archive.namelist() if name.startswith("conversations/")]) == 1
            )
            assert "B 的私有对话" not in "\n".join(
                archive.read(name).decode("utf-8") for name in archive.namelist()
            )
            assert not any("settings" in name or "key" in name for name in archive.namelist())
        assert client.delete(f"/api/projects/{first['id']}").status_code == 200
        assert (
            client.get(materials(first) + "/" + saved.json()["id"] + "?version=1").status_code
            == 200
        )


def test_multiple_roots_paths_evidence_and_detachment(services, tmp_path):
    paths = services[0]
    other = tmp_path / "interfaces"
    other.mkdir()
    (other / "Program.cs").write_text(
        "class Secondary {\n static void Main() {}\n}\n", encoding="utf-8"
    )
    app = create_app(paths)
    with TestClient(app) as client:
        saved = project(
            client, "多目录", str(paths.workspace), [{"root": str(other), "label": "设备接口"}]
        )
        folder = saved["source_folders"][0]
        scoped = f"/api/p/{saved['id']}"
        entries = client.get(scoped + "/files").json()
        prefix = "@sources/" + folder["source_id"] + "/"
        assert entries[0]["name"] == "设备接口"
        source = client.get(scoped + "/file", params={"path": prefix + "Program.cs"}).json()
        assert "Secondary" in source["content"]
        assert source["source_workspace_id"] == folder["source_id"]
        assert "Program {" in client.get(scoped + "/file?path=Program.cs").json()["content"]
        search = client.get(scoped + "/search?query=Main").json()["matches"]
        assert {row["path"] for row in search} == {"Program.cs", prefix + "Program.cs"}
        workspace = app.state.projects.services(saved["id"]).workspace
        evidence = SourceEvidence(workspace, lambda *_: None)
        evidence.record(source_excerpt(workspace, prefix + "Program.cs", 1, 3))
        assert evidence.reads[0]["source_workspace_id"] == folder["source_id"]
        assert evidence.check(f"[引用](source:{prefix}Program.cs#L1)")["passed"]
        assert any(
            item["path"].endswith(prefix + "Program.cs")
            for item in SourceBackend(workspace).glob("*.cs").matches
        )
        assert (
            client.get(scoped + "/file", params={"path": prefix + "../outside"}).status_code == 409
        )
        assert (
            client.patch(f"/api/projects/{saved['id']}", json={"source_folders": []}).status_code
            == 200
        )
        assert (
            client.get(scoped + "/file", params={"path": prefix + "Program.cs"}).status_code == 404
        )
        historic = client.get(
            f"/api/sources/{folder['source_id']}/file", params={"path": prefix + "Program.cs"}
        )
        assert historic.status_code == 200 and "Secondary" in historic.json()["content"]
        assert (other / "Program.cs").exists()
        duplicate = client.patch(
            f"/api/projects/{saved['id']}",
            json={"source_folders": [{"root": str(paths.workspace), "label": "重复"}]},
        )
        assert duplicate.status_code == 409
