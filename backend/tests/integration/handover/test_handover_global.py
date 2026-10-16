"""全局交接不依赖聊天项目，升级保留原件、版本、引用和操作历史。"""

import importlib
import json

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient

from app.infrastructure.database.base import Base
from app.main import create_app
from app.modules.handover.infrastructure.persistence.models import HandoverRecord


def test_global_records_survive_dialog_project_changes_and_new_writes(services):
    with TestClient(create_app(services[0])) as client:
        first = client.post("/api/projects", json={"name": "对话 A"}).json()["id"]
        second = client.post("/api/projects", json={"name": "对话 B"}).json()["id"]
        row = client.post(
            "/api/handover/records",
            json={
                "kind": "interview",
                "title": "全局笔录",
                "actor": "整理人",
                "payload": {"transcript": "原作者说明，尚未核验。"},
            },
        ).json()
        before = client.get("/api/handover").json()
        assert row["scope_id"] == "global" and row["source_project_id"] is None
        for project_id in (first, second):
            client.patch(f"/api/projects/{project_id}", json={"state": "archived"})
            assert client.get("/api/handover").json() == before
        changed = client.patch(
            f"/api/handover/records/{row['id']}",
            json={
                "kind": "interview",
                "title": row["title"],
                "actor": "接手人",
                "version": 1,
                "payload": {"transcript": "补充全局笔录"},
            },
        )
        assert changed.status_code == 200
        assert (
            client.get(f"/api/handover/records/{row['id']}?version=1").json()["payload"][
                "transcript"
            ]
            == "原作者说明，尚未核验。"
        )
        context = client.get("/api/handover/context").json()
        assert context["scope_id"] == "global" and "source_projects" in context
        assert client.get(f"/api/projects/{first}/handover").status_code == 404


def test_project_material_origin_is_explicit_and_does_not_own_handover(services):
    with TestClient(create_app(services[0])) as client:
        project = client.post("/api/projects", json={"name": "资料来源"}).json()["id"]
        material = client.post(
            f"/api/projects/{project}/materials",
            json={
                "title": "需求笔记",
                "content": "仅作为导入来源",
            },
        ).json()
        body = {"actor": "整理人", "version": 1, "opinion": "保留来源版本"}
        path = f"/api/handover/sources/material/{material['id']}"
        assert client.post(path, json=body).status_code == 422
        imported = client.post(path, json={**body, "source_project_id": project})
        assert imported.status_code == 201
        row = imported.json()
        assert row["payload"]["source_project_id"] == project
        client.patch(f"/api/projects/{project}", json={"state": "archived"})
        assert (
            client.get(f"/api/handover/sources/{row['id']}/original").content
            == "仅作为导入来源".encode()
        )
        assert client.get(f"/api/projects/{project}/materials/{material['id']}").json() == material


def test_legacy_migration_preserves_attachment_versions_and_global_references(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "旧交接来源"}).json()["id"]
    engine = app.state.projects.database.engine
    names = ("handover_records", "handover_revisions", "handover_blobs", "handover_events")
    migration = importlib.import_module("migrations.versions.0014_global_handover")
    with engine.begin() as connection:
        # 构造带项目外键的旧版表，覆盖真实升级路径，而非新安装的空表路径。
        for name in reversed(names):
            connection.exec_driver_sql(f"DROP TABLE {name}")
        metadata = sa.MetaData()
        sa.Table("projects", metadata, autoload_with=connection)
        for name in names:
            columns = []
            for column in Base.metadata.tables[name].columns:
                key = "project_id" if column.name == "source_project_id" else column.name
                foreign_keys = (
                    [sa.ForeignKey("projects.id")]
                    if key == "project_id"
                    else [sa.ForeignKey("handover_records.id")]
                    if key == "record_id"
                    else []
                )
                columns.append(
                    sa.Column(
                        key,
                        column.type,
                        *foreign_keys,
                        primary_key=column.primary_key,
                        nullable=False if key == "project_id" else column.nullable,
                    )
                )
            sa.Table(name, metadata, *columns).create(connection)
        payload = json.dumps({"content": "旧模拟原文", "source_version": "v1"}, ensure_ascii=False)
        connection.execute(
            sa.text(
                "INSERT INTO handover_records VALUES "
                "(:id,:project,'source','旧资料',2,'confirmed',:payload,'old-time','old-time')"
            ),
            {"id": "old-source", "project": project, "payload": payload},
        )
        connection.execute(
            sa.text(
                "INSERT INTO handover_revisions VALUES "
                "(1,'old-source',1,'旧资料','draft',:payload,'{}','old-time')"
            ),
            {"payload": payload},
        )
        connection.execute(
            sa.text(
                "INSERT INTO handover_revisions VALUES "
                "(2,'old-source',2,'旧资料','confirmed',:payload,:confirmation,'old-time')"
            ),
            {"payload": payload, "confirmation": '{"actor":"旧审核人"}'},
        )
        connection.execute(
            sa.text(
                "INSERT INTO handover_blobs VALUES "
                "('old-source','old.txt','text/plain',:hash,:content)"
            ),
            {"hash": "original-hash", "content": b"original bytes"},
        )
        connection.execute(
            sa.text(
                "INSERT INTO handover_events VALUES "
                "(1,:project,'old-source','confirm','旧审核人','old detail',2,'old-time')"
            ),
            {"project": project},
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert not connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        assert "project_id" not in {
            col["name"] for col in sa.inspect(connection).get_columns(names[0])
        }
        assert all(
            fk["referred_table"] != "projects"
            for name in names
            for fk in sa.inspect(connection).get_foreign_keys(name)
        )
        assert connection.scalar(sa.select(HandoverRecord.source_project_id)) == project
        assert (
            connection.exec_driver_sql("SELECT content FROM handover_blobs").scalar()
            == b"original bytes"
        )
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM handover_revisions").scalar() == 2
        assert (
            connection.exec_driver_sql("SELECT actor FROM handover_events").scalar() == "旧审核人"
        )
    with TestClient(create_app(services[0])) as client:
        record = client.get("/api/handover/records/old-source").json()
        assert record["scope_id"] == "global" and record["confirmation"]["actor"] == "旧审核人"
        assert (
            client.get("/api/handover/records/old-source?version=1").json()["payload"]["content"]
            == "旧模拟原文"
        )
        assert client.get("/api/handover/sources/old-source/original").content == b"original bytes"
