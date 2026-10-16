"""交接业务的隔离、验收门槛、固定证据和原模块边界。"""

import io
import json
import time
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.handover.imports import parse_docx
from app.main import create_app


@pytest.fixture
def client(services):
    with TestClient(create_app(services[0])) as value:
        yield value


def project(client, name="A", root=None):
    return client.post("/api/projects", json={"name": name, "source_root": root}).json()["id"]


def url(project_id):
    return "/api/handover"


def create(client, project_id, kind, title, **payload):
    response = client.post(
        url(project_id) + "/records",
        json={"kind": kind, "title": title, "actor": "整理人", "payload": payload},
    )
    assert response.status_code == 201, response.text
    return response.json()


def action(client, project_id, row, action="confirm"):
    return client.post(
        url(project_id) + f"/records/{row['id']}/{action}",
        json={
            "version": row["version"],
            "actor": "设备负责人",
            "role": "原作者",
            "opinion": "已复核此版本及来源",
        },
    )


def update(client, project_id, row, **payload):
    return client.patch(
        url(project_id) + f"/records/{row['id']}",
        json={
            "kind": row["kind"],
            "title": row["title"],
            "payload": {**row["payload"], **payload},
            "actor": "更正人",
            "reason": "补充设备验证",
            "version": row["version"],
        },
    )


def source(client, project_id, filename="source.txt", data=None):
    if data is None:
        data = "原作者说明：设备必须停止后才能复位。".encode()
    response = client.post(
        url(project_id) + "/sources/import",
        params={
            "filename": filename,
            "actor": "整理人",
            "provider": "原作者",
            "source_version": "V1",
            "device": "测试设备",
        },
        content=data,
    )
    assert response.status_code == 201, response.text
    return response.json()


def baseline(client, project_id):
    raw = source(client, project_id, "baseline.cs", b"class Controller {}")
    row = create(
        client,
        project_id,
        "baseline",
        "接收环境",
        source_id=raw["id"],
        source_scope="Controller.cs 离线验收范围",
        software_version="V1",
        device="设备 A",
        firmware="1",
        sdk="2",
        recipe="不适用",
        calibration="不适用",
        configuration="QA 配置",
        build="安装 SDK 后编译",
        environment="设备 A 台架",
    )
    confirmed = action(client, project_id, row)
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()


def test_global_history_optimistic_version_and_dialog_project_archive(client):
    first, second = project(client), project(client, "B")
    row = create(
        client,
        first,
        "interview",
        "交接访谈",
        author="工程师",
        date="2026-10-12",
        transcript="报警恢复尚未设备验证",
    )
    assert client.get(url(second) + f"/records/{row['id']}").json()["scope_id"] == "global"
    confirmed = action(client, first, row).json()
    edited = update(client, first, confirmed, correction="先离线验证").json()
    assert edited["state"] == "needs_review"
    old = client.get(url(first) + f"/records/{row['id']}?version={confirmed['version']}").json()
    assert old["state"] == "confirmed" and old["payload"]["correction"] == ""
    assert old["confirmation"]["actor"] == "设备负责人"
    assert update(client, first, confirmed, correction="过期编辑").status_code == 409
    assert action(client, first, confirmed).status_code == 409
    client.patch(f"/api/projects/{first}", json={"state": "archived"})
    assert update(client, first, edited, correction="对话项目归档后仍可编辑").status_code == 200
    assert client.get(url(first)).status_code == 200
    assert client.get(url(first) + "/events").json()[0]["actor"] == "更正人"


def test_layered_acceptance_and_high_risk_blocks(client):
    identifier = project(client)
    base = baseline(client, identifier)
    task = create(
        client,
        identifier,
        "task",
        "报警恢复",
        goal="恢复流程",
        acceptance="设备完成恢复且轴无异常运动",
        owner="接手人",
        baseline_id=base["id"],
        work_status="accepted",
    )
    assert action(client, identifier, task).status_code == 409
    verification = create(
        client,
        identifier,
        "verification",
        "离线检查",
        task_id=task["id"],
        baseline_id=base["id"],
        layer="offline",
        result="pass",
        tester="测试人",
        date="2026-10-12",
        environment="离线",
        method="单元检查",
        observed="通过",
        report="报告 A",
    )
    verification = action(client, identifier, verification).json()
    assert verification["state"] == "confirmed"
    assert action(client, identifier, task).status_code == 409
    verification = update(client, identifier, verification, layer="device").json()
    assert action(client, identifier, verification).status_code == 200
    issue = create(
        client,
        identifier,
        "issue",
        "联锁条件未知",
        task_id=task["id"],
        risk="critical",
        question="门禁联锁何时允许复位",
        owner="原作者",
    )
    assert action(client, identifier, task).status_code == 409
    assert (
        update(
            client, identifier, issue, status="resolved", answer="确认", closure="记录"
        ).status_code
        == 409
    )
    evidence = source(client, identifier)
    issue = update(
        client,
        identifier,
        issue,
        status="resolved",
        answer="先确认门禁状态",
        closure="原作者说明",
        evidence=[{"record_id": evidence["id"], "version": evidence["version"]}],
    ).json()
    assert action(client, identifier, issue).status_code == 200
    verification = client.get(url(identifier) + f"/records/{verification['id']}").json()
    assert action(client, identifier, verification).status_code == 200
    confirmed = action(client, identifier, task)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["payload"]["evidence_status"] == "unknown"


def test_dependency_cycles_plan_conditions_and_invalidation(client):
    identifier = project(client)
    base = baseline(client, identifier)
    a = create(
        client,
        identifier,
        "task",
        "工作 A",
        goal="A",
        acceptance="A 通过",
        owner="人",
        baseline_id=base["id"],
    )
    b = create(client, identifier, "task", "工作 B", dependencies=[a["id"]])
    assert update(client, identifier, a, dependencies=[b["id"]]).status_code == 409
    a = action(client, identifier, a).json()
    plan = create(
        client,
        identifier,
        "plan",
        "接续步骤",
        task_id=a["id"],
        baseline_id=base["id"],
        steps=[{"action": "离线测试"}],
    )
    assert action(client, identifier, plan).status_code == 409
    step = {
        key: "明确内容"
        for key in ("action", "prerequisite", "output", "verification", "stop", "rollback", "owner")
    }
    plan = update(client, identifier, plan, steps=[step]).json()
    approved = action(client, identifier, plan)
    assert approved.status_code == 200, approved.text
    old = approved.json()
    safety = create(
        client,
        identifier,
        "constraint",
        "门禁",
        category="safety",
        condition="门关闭",
        consequence="否则不允许运动",
        authority="设备负责人",
        stop_condition="门打开停机",
    )
    current = client.get(url(identifier) + f"/records/{old['id']}").json()
    assert current["state"] == "needs_review"
    assert (
        client.get(url(identifier) + f"/records/{old['id']}?version={old['version']}").json()[
            "state"
        ]
        == "confirmed"
    )
    assert action(client, identifier, current).status_code == 409
    assert action(client, identifier, safety).status_code == 200
    a = client.get(url(identifier) + f"/records/{a['id']}").json()
    assert action(client, identifier, a).status_code == 200
    assert action(client, identifier, current).status_code == 200


def test_source_files_fixed_versions_quotations_and_exports(client, services):
    identifier = project(client, root=str(services[0].workspace))
    captured = client.post(
        url(identifier) + "/sources/capture",
        json={
            "path": "Program.cs",
            "source_project_id": identifier,
            "actor": "整理人",
            "provider": "仓库",
            "source_version": "固定快照",
        },
    ).json()
    assert captured["payload"]["sha256"]
    assert not client.get(url(identifier) + f"/sources/{captured['id']}/compare").json()["changed"]
    other_root = services[0].workspace.parent / "same-code-other-root"
    other_root.mkdir()
    (other_root / "Program.cs").write_bytes((services[0].workspace / "Program.cs").read_bytes())
    client.patch(f"/api/projects/{identifier}", json={"source_root": str(other_root)})
    comparison = client.get(url(identifier) + f"/sources/{captured['id']}/compare").json()
    assert comparison["changed"] and comparison["saved_sha256"] == comparison["current_sha256"]
    client.patch(f"/api/projects/{identifier}", json={"source_root": str(services[0].workspace)})
    (services[0].workspace / "Program.cs").write_text("class New {}", encoding="utf-8")
    assert client.get(url(identifier) + f"/sources/{captured['id']}/compare").json()["changed"]
    original = client.get(url(identifier) + f"/sources/{captured['id']}/original")
    assert b"class Program" in original.content
    response = client.post(
        url(identifier) + "/records",
        json={
            "kind": "task",
            "title": "假的引文",
            "actor": "人",
            "payload": {
                "evidence": [{"record_id": captured["id"], "version": 1, "quote": "设备验证通过"}]
            },
        },
    )
    assert response.status_code == 409
    row = create(
        client,
        identifier,
        "task",
        "真实任务",
        goal="未完成",
        notes="包含 <符号> & 文本",
        evidence=[{"record_id": captured["id"], "version": 1, "quote": "class Program"}],
    )
    package = client.post(
        url(identifier) + "/packages",
        json={"title": "交接包", "actor": "人", "record_ids": [row["id"], captured["id"]]},
    ).json()
    word = client.get(url(identifier) + f"/packages/{package['id']}/export")
    assert word.status_code == 200 and word.content[:2] == b"PK"
    content, _, _, _ = parse_docx(word.content)
    assert "包含 <符号> & 文本" in content and "待确认" in content and "class Program" in content
    update(client, identifier, row, goal="新目标")
    assert (
        "新目标"
        not in parse_docx(
            client.get(url(identifier) + f"/packages/{package['id']}/export").content
        )[0]
    )
    archive = zipfile.ZipFile(
        io.BytesIO(
            client.get(url(identifier) + f"/packages/{package['id']}/export?format=zip").content
        )
    )
    assert "handover.docx" in archive.namelist() and any(
        name.endswith("Program.cs") for name in archive.namelist()
    )


def test_zip_readonly_paths_docx_and_project_material_capture(client):
    identifier = project(client)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("src/Program.cs", "class Motor {}")
    imported = source(client, identifier, "source.zip", stream.getvalue())
    file = client.get(
        url(identifier) + f"/sources/{imported['id']}/file", params={"path": "src/Program.cs"}
    ).json()
    assert file["content"] == "class Motor {}"
    assert (
        client.get(
            url(identifier) + f"/sources/{imported['id']}/file", params={"path": "../secret"}
        ).status_code
        == 404
    )
    unsafe = io.BytesIO()
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("../unsafe.cs", "class Unsafe {}")
    assert (
        client.post(
            url(identifier) + "/sources/import?filename=source.zip&actor=人",
            content=unsafe.getvalue(),
        ).status_code
        == 409
    )
    material = client.post(
        f"/api/projects/{identifier}/materials", json={"title": "现有资料", "content": "原内容"}
    ).json()
    captured = client.post(
        url(identifier) + f"/sources/material/{material['id']}",
        json={
            "version": 1,
            "actor": "人",
            "opinion": "选择固定版本",
            "source_project_id": identifier,
        },
    )
    assert captured.status_code == 201
    assert client.get(f"/api/projects/{identifier}/materials/{material['id']}").json() == material


def poll_job(client, identifier, job):
    for _ in range(100):
        result = client.get(url(identifier) + f"/records/{job['id']}").json()
        if result["payload"]["status"] not in {"queued", "running"}:
            return result
        time.sleep(0.01)
    pytest.fail("AI 作业未结束")


def test_ai_candidates_need_human_merge_and_reject_invented_sources(client, monkeypatch):
    identifier = project(client)
    raw = source(client, identifier)
    proposal = {
        "candidates": [
            {
                "title": "待实现复位",
                "payload": {
                    "target_kind": "task",
                    "proposed": {"goal": "复位"},
                    "evidence": [
                        {"record_id": raw["id"], "version": 1, "quote": "设备必须停止后才能复位。"}
                    ],
                },
            }
        ]
    }

    class Model:
        async def ainvoke(self, _messages):
            return SimpleNamespace(text=json.dumps(proposal))

    monkeypatch.setattr("app.handover.ai.create_model", lambda _settings: Model())
    monkeypatch.setattr("app.handover.ai.close_models", no_close)
    job = client.post(
        url(identifier) + "/ai",
        json={"action": "extract", "record_ids": [raw["id"]], "actor": "人"},
    ).json()
    completed = poll_job(client, identifier, job)
    assert completed["payload"]["status"] == "succeeded", completed
    candidate_id = completed["payload"]["result_ids"][0]
    candidate = client.get(url(identifier) + f"/records/{candidate_id}").json()
    assert action(client, identifier, candidate).status_code == 409
    body = {
        "version": 1,
        "actor": "审核人",
        "opinion": "核对原文并修订目标",
        "title": "复位工作",
        "proposed": {"goal": "人工修订后复位", "owner": "接手人"},
    }
    merged = client.post(url(identifier) + f"/candidates/{candidate_id}/promote", json=body)
    assert merged.status_code == 201 and merged.json()["state"] == "draft"
    assert merged.json()["payload"]["origin"] == "ai"
    assert (
        client.post(url(identifier) + f"/candidates/{candidate_id}/promote", json=body).status_code
        == 409
    )
    proposal["candidates"][0]["payload"]["evidence"][0]["record_id"] = "fake"
    failed = client.post(
        url(identifier) + "/ai",
        json={"action": "extract", "record_ids": [raw["id"]], "actor": "人"},
    ).json()
    assert poll_job(client, identifier, failed)["payload"]["status"] == "failed"


async def no_close(_models):
    pass
