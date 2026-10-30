"""已删除功能没有运行入口；迁移和完整备份继续保存旧数据。"""

import io
import json
import zipfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.agents.runtime.engine import AgentRuntime
from app.infrastructure.database.registry import Base
from app.infrastructure.database.session import Database
from app.main import create_app
from app.modules.chat.context import ConversationContext
from app.modules.source_analysis.backend import SourceBackend
from app.modules.source_analysis.evidence import SourceEvidence, source_excerpt

HISTORICAL_TABLES = (
    "project_materials",
    "project_material_revisions",
    "project_reading_jobs",
    "project_reading_files",
    "project_reading_documents",
)


def project(client, name, root=None, folders=None):
    response = client.post(
        "/api/projects", json={"name": name, "source_root": root, "source_folders": folders or []}
    )
    assert response.status_code == 201, response.text
    return response.json()


def seed_history(database, project_id):
    # 用旧表的真实 SQL 快照准备回归，不恢复已删除的业务模型或接口。
    with database.engine.begin() as connection:
        for kind in ("document", "conclusion"):
            connection.exec_driver_sql(
                "INSERT INTO project_materials "
                "(id,project_id,title,kind,source_name,content,version,state,"
                "created_at,updated_at) "
                "VALUES (?,?,?,?,'','旧正文',1,'deleted','2026-10-01','2026-10-01')",
                (kind, project_id, "历史资料", kind),
            )
            connection.exec_driver_sql(
                "INSERT INTO project_material_revisions "
                "(material_id,version,title,content,created_at) "
                "VALUES (?,1,'历史资料','固定版本原文','2026-10-01')",
                (kind,),
            )
        connection.exec_driver_sql(
            "INSERT INTO project_reading_jobs "
            "(id,project_id,title,status,snapshot_version,created_at,updated_at,error) "
            "VALUES ('legacy-job',?,'旧任务','running','','2026-10-01','2026-10-01','')",
            (project_id,),
        )
        connection.exec_driver_sql(
            "INSERT INTO project_reading_files "
            "(id,project_id,job_id,path,module,source_version,encoding,status,"
            "indexed,read,analyzed,reviewed,stale,next_chunk,read_chunks,error) "
            "VALUES ('legacy-file',?,'legacy-job','Program.cs','入口','','utf-8',"
            "'analyzed',1,1,1,0,0,1,1,'')",
            (project_id,),
        )
        connection.exec_driver_sql(
            "INSERT INTO project_reading_documents "
            "(id,project_id,job_id,file_id,path,module,chunk_index,version,source_version,"
            "start_line,end_line,status,latest,summary,entrypoints_json,dependencies_json,"
            "unknowns_json,references_json,created_at) "
            "VALUES ('legacy-doc',?,'legacy-job','legacy-file','Program.cs','入口',0,1,'',"
            "1,3,'analyzed',1,'历史阅读成果','[]','[]','[]','[]','2026-10-01')",
            (project_id,),
        )


def history_snapshot(database):
    with database.engine.connect() as connection:
        return {
            name: list(connection.exec_driver_sql(f'SELECT * FROM "{name}" ORDER BY id'))
            for name in HISTORICAL_TABLES
        }


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("GET", "/materials", None),
        ("GET", "/materials/document?version=1", None),
        ("GET", "/materials/conclusion?version=1", None),
        ("POST", "/materials", {"title": "新资料", "content": "不能写入"}),
        ("PATCH", "/materials/document", {"version": 1, "content": "不能修改"}),
        ("GET", "/project-reading", None),
        ("POST", "/project-reading", {"title": "不能开始"}),
        ("POST", "/project-reading/legacy-job/start", {}),
        ("GET", "/project-reading/legacy-job/documents", None),
    ],
)
def test_retired_routes_cannot_read_or_change_preserved_history(services, method, suffix, body):
    app = create_app(services[0])
    with TestClient(app) as client:
        saved = project(client, "已退出功能")
        database = app.state.projects.database
        seed_history(database, saved["id"])
        before = history_snapshot(database)
        prefix = (
            f"/api/p/{saved['id']}"
            if suffix.startswith("/project-reading")
            else f"/api/projects/{saved['id']}"
        )
        response = client.request(method, prefix + suffix, json=body)
        assert response.status_code in {404, 405}, response.text
        assert history_snapshot(database) == before


def test_archive_and_backup_work_without_runtime_models_or_material_exports(services):
    assert not set(HISTORICAL_TABLES) & Base.metadata.tables.keys()
    with TestClient(create_app(services[0])) as client:
        saved = project(client, "旧历史仍保留")
        thread = client.post(f"/api/p/{saved['id']}/threads", json={}).json()
        database = client.app.state.projects.database
        seed_history(database, saved["id"])
        before = history_snapshot(database)
        assert client.post("/api/backup").status_code == 200
        exported = client.get(f"/api/projects/{saved['id']}/export")
        assert exported.status_code == 200
        assert exported.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            assert not any(name.startswith("materials/") for name in archive.namelist())
            assert json.loads(archive.read("project.json"))["name"] == saved["name"]
            conversation = json.loads(archive.read(f"conversations/{thread['id']}.json"))
            assert conversation["id"] == thread["id"]
            assert json.loads(archive.read("memories.json")) == []
        assert (
            client.patch(f"/api/projects/{saved['id']}", json={"state": "archived"}).status_code
            == 200
        )
        assert history_snapshot(database) == before


def test_fresh_migrations_are_independent_of_retired_application_models(tmp_path):
    database = Database(tmp_path / "fresh.sqlite3")
    config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    config.attributes["connection"] = database.engine
    try:
        command.upgrade(config, "0011")
        assert set(HISTORICAL_TABLES[:2]) <= set(inspect(database.engine).get_table_names())
        command.downgrade(config, "0010")
        assert set(HISTORICAL_TABLES).isdisjoint(inspect(database.engine).get_table_names())
        command.upgrade(config, "0019")
        command.downgrade(config, "0018")
        assert set(HISTORICAL_TABLES[2:]).isdisjoint(inspect(database.engine).get_table_names())
        command.upgrade(config, "head")
        schema = inspect(database.engine)
        assert set(HISTORICAL_TABLES) <= set(schema.get_table_names())
        assert {"description", "instructions"}.isdisjoint(
            row["name"] for row in schema.get_columns("projects")
        )
        assert any(row["unique"] for row in schema.get_indexes("project_material_revisions"))
        with database.engine.connect() as connection:
            assert not list(connection.exec_driver_sql("PRAGMA foreign_key_check"))
    finally:
        database.close()


def test_historical_events_do_not_restore_retired_sources(services):
    paths, _, workspace, repository, memories, settings = services
    run = repository.create_run(None, "查询当前问题", [])
    old_reference = {
        "kind": "material",
        "id": "old",
        "version": 1,
        "title": "旧项目资料",
        "citation": "material:project/old/1#L1",
    }
    issue = {
        "kind": "debug_issue",
        "id": "issue",
        "version": 2,
        "title": "历史问题",
        "citation": "debug-issue:issue/2",
    }
    for kind, payload in (
        (
            "context_sources",
            {"memories": [], "materials": [old_reference], "debug_issues": [issue]},
        ),
        ("knowledge_reference", old_reference),
        ("knowledge_reference", issue),
        ("knowledge_search", {"kind": "material", "matched": 1}),
        ("knowledge_search", {"kind": "debug_issue", "matched": 1}),
    ):
        repository.event(run["id"], kind, payload)
    before = repository.events(run["id"])
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    snapshot = ConversationContext(runtime).run_sources(run["id"])
    assert "materials" not in snapshot
    assert snapshot["references"] == [issue]
    assert snapshot["debug_issues"] == [issue]
    assert snapshot["searches"] == [{"kind": "debug_issue", "matched": 1}]
    assert repository.events(run["id"]) == before


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
