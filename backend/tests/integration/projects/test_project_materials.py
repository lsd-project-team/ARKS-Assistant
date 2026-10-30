"""项目资料管理与全项目阅读退出；旧引用、项目归档和源码能力保留。"""

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.modules.projects.models import ProjectMaterial, ProjectMaterialRevision
from app.modules.source_analysis.backend import SourceBackend
from app.modules.source_analysis.evidence import SourceEvidence, source_excerpt
from app.modules.source_analysis.reading.models import ProjectReadingJob


def project(client, name, root=None, folders=None):
    response = client.post(
        "/api/projects", json={"name": name, "source_root": root, "source_folders": folders or []}
    )
    assert response.status_code == 201, response.text
    return response.json()


def materials(project):
    return f"/api/projects/{project['id']}/materials"


def seed_material(database, project_id, kind="document"):
    # 仅准备历史快照；正式应用已没有资料创建、更新或检索路径。
    with database.session.begin() as session:
        row = ProjectMaterial(
            project_id=project_id,
            title="历史报警说明",
            content="新版归档正文",
            kind=kind,
            state="deleted",
            version=2,
        )
        session.add(row)
        session.flush()
        for version, content in ((1, "报警处理：先确认轴停止。"), (2, row.content)):
            session.add(
                ProjectMaterialRevision(
                    material_id=row.id,
                    version=version,
                    title=row.title,
                    content=content,
                )
            )
        return row.id


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("GET", "/materials", None),
        ("POST", "/materials", {"title": "新资料", "content": "不能写入"}),
        ("POST", "/materials", {"title": "旧结论", "content": "不能写入", "kind": "conclusion"}),
        ("PATCH", "/materials/{id}", {"version": 2, "content": "不能修改"}),
        ("GET", "/project-reading", None),
        ("POST", "/project-reading", {"title": "不能开始"}),
        ("POST", "/project-reading/legacy-job/start", {}),
        ("GET", "/project-reading/legacy-job/documents", None),
    ],
)
def test_removed_management_and_reading_routes_leave_history_unchanged(
    services, method, suffix, body
):
    app = create_app(services[0])
    with TestClient(app) as client:
        saved = project(client, "已退出功能")
        database = app.state.projects.database
        identifier = seed_material(database, saved["id"])
        prefix = (
            f"/api/p/{saved['id']}"
            if suffix.startswith("/project-reading")
            else f"/api/projects/{saved['id']}"
        )
        response = client.request(method, prefix + suffix.format(id=identifier), json=body)
        assert response.status_code in {404, 405}, response.text
        with database.session() as session:
            row = session.get(ProjectMaterial, identifier)
            assert row.version == 2 and row.content == "新版归档正文"
            assert len(list(session.scalars(select(ProjectMaterial)))) == 1
            assert len(list(session.scalars(select(ProjectMaterialRevision)))) == 2
            assert list(session.scalars(select(ProjectReadingJob))) == []


@pytest.mark.parametrize("kind", ["document", "conclusion"])
def test_historical_fixed_version_read_and_export_still_enforce_project_scope(services, kind):
    app = create_app(services[0])
    with TestClient(app) as client:
        first, second = project(client, "A"), project(client, "B")
        database = app.state.projects.database
        identifier = seed_material(database, first["id"], kind)
        url = materials(first) + "/" + identifier
        assert client.get(url).status_code == 422
        first_version = client.get(url + "?version=1")
        assert first_version.status_code == 200
        assert first_version.json()["content"] == "报警处理：先确认轴停止。"
        assert first_version.json()["version"] == 1
        assert first_version.json()["kind"] == kind
        assert client.get(url + "?version=2").json()["content"] == "新版归档正文"
        assert client.get(url + "?version=3").status_code == 404
        assert client.get(materials(second) + "/" + identifier + "?version=1").status_code == 404
        exported = client.get(f"/api/projects/{first['id']}/export")
        assert exported.status_code == 200
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            record = json.loads(archive.read(f"materials/{identifier}.json"))
            assert record["kind"] == kind
            assert [row["content"] for row in record["revisions"]] == [
                "报警处理：先确认轴停止。",
                "新版归档正文",
            ]
        assert client.delete(f"/api/projects/{first['id']}").status_code == 200
        assert client.get(url + "?version=1").json()["content"] == "报警处理：先确认轴停止。"


def test_retired_reading_state_does_not_block_backup_or_project_archive(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        saved = project(client, "旧阅读状态")
        database = app.state.projects.database
        with database.session.begin() as session:
            session.add(
                ProjectReadingJob(
                    id="legacy-job", project_id=saved["id"], title="旧任务", status="running"
                )
            )
        assert client.post("/api/backup").status_code == 200
        assert (
            client.patch(f"/api/projects/{saved['id']}", json={"state": "archived"}).status_code
            == 200
        )
        with database.session() as session:
            assert session.get(ProjectReadingJob, "legacy-job").title == "旧任务"


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
