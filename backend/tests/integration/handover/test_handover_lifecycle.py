"""资料更新影响、接收记录与设备验收门槛。"""

import io

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import create_app
from app.modules.handover.infrastructure.parsers.docx import parse_docx
from app.modules.handover.infrastructure.parsers.pdf import parse_pdf
from app.modules.handover.infrastructure.persistence.repository import HandoverStore


def test_framework_training_decision_receipt_and_package_sources(services):
    with TestClient(create_app(services[0])) as client:
        root = "/api/handover"

        def create(kind, title, payload):
            result = client.post(
                root + "/records",
                json={"kind": kind, "title": title, "payload": payload, "actor": "整理人"},
            )
            assert result.status_code == 201, result.text
            return result.json()

        def confirm(row):
            result = client.post(
                root + f"/records/{row['id']}/confirm",
                json={
                    "version": row["version"],
                    "actor": "原作者",
                    "role": "负责人",
                    "opinion": "已复核内容、来源与范围",
                },
            )
            assert result.status_code == 200, result.text
            return result.json()

        source = client.post(
            root
            + "/sources/import?filename=readme.txt&actor=整理人&provider=原作者&source_version=1",
            content="框架包含入口和复位模块，操作前须确认停止状态。".encode(),
        ).json()
        evidence = [
            {
                "record_id": source["id"],
                "version": source["version"],
                "quote": "操作前须确认停止状态。",
            }
        ]
        framework = confirm(
            create(
                "framework",
                "框架",
                {
                    "scope": "复位模块",
                    "entrypoints": "入口",
                    "layers": "入口调用控制层",
                    "flow": "状态确认后调用",
                    "coverage": "仅复位模块",
                    "missing": "其他模块未分析",
                    "evidence": evidence,
                },
            )
        )
        training = confirm(
            create(
                "training",
                "复位培训",
                {
                    "conditions": "停止状态",
                    "operation": "确认状态再复位",
                    "timing": "读取反馈后处理",
                    "failure": "超时",
                    "recovery": "停止并排查",
                    "exercise": "离线复述流程",
                    "feedback": "待现场练习",
                    "evidence": evidence,
                },
            )
        )
        decision = confirm(
            create(
                "decision",
                "原设计意图",
                {
                    "intent": "复位独立",
                    "alternatives": "合并自动流程",
                    "rejected": "复位不得触发自动启动",
                    "evidence": evidence,
                },
            )
        )
        package = client.post(
            root + "/packages",
            json={
                "title": "交接包",
                "actor": "整理人",
                "record_ids": [framework["id"], training["id"], decision["id"]],
            },
        ).json()
        assert {ref["record_id"] for ref in package["payload"]["records"]} == {
            source["id"],
            framework["id"],
            training["id"],
            decision["id"],
        }
        package = confirm(package)
        receipt = confirm(
            create(
                "receipt",
                "接收记录",
                {
                    "package_id": package["id"],
                    "package_version": package["version"],
                    "receiver": "接手人",
                    "date": "2026-10-12",
                    "understanding": "复述停止前提和模块边界",
                    "demonstration": "离线演示",
                    "remaining": "等待设备验证",
                },
            )
        )
        assert receipt["state"] == "confirmed"
        bad = client.post(
            root + "/records",
            json={
                "kind": "receipt",
                "title": "虚构版本",
                "actor": "人",
                "payload": {"package_id": package["id"], "package_version": 999},
            },
        )
        assert bad.status_code == 404
        word = client.get(root + f"/packages/{package['id']}/export").content
        content = parse_docx(word)[0]
        for expected in ("仅复位模块", "其他模块未分析", "原设计", "操作前须确认停止状态。"):
            assert expected in content


def test_scanned_pdf_records_missing_text_instead_of_fake_success():
    writer, stream = PdfWriter(), io.BytesIO()
    writer.add_blank_page(width=300, height=300)
    writer.write(stream)
    content, status, notes, _files = parse_pdf(stream.getvalue())
    assert status == "needs_ocr" and "[1]" in notes and "第 1 页" in content


def test_replaced_source_keeps_original_and_requires_downstream_review(services):
    with TestClient(create_app(services[0])) as client:
        root = "/api/handover"
        source = client.post(
            root + "/sources/import?filename=original.txt&actor=人&provider=作者&source_version=1",
            content="原版说明".encode(),
        ).json()
        task = client.post(
            root + "/records",
            json={
                "kind": "task",
                "title": "工作",
                "actor": "人",
                "payload": {
                    "goal": "完成工作",
                    "owner": "接手人",
                    "acceptance": "通过检查",
                    "evidence": [{"record_id": source["id"], "version": 1}],
                },
            },
        ).json()
        approved = client.post(
            root + f"/records/{task['id']}/confirm",
            json={"version": 1, "actor": "作者", "opinion": "确认原版"},
        ).json()
        response = client.post(
            root + "/sources/import",
            params={
                "filename": "replacement.txt",
                "actor": "人",
                "provider": "作者",
                "source_version": "2",
                "supersedes": source["id"],
            },
            content="更正后的说明".encode(),
        )
        assert response.status_code == 201, response.text
        current = client.get(root + f"/records/{task['id']}").json()
        assert current["state"] == "needs_review"
        assert (
            client.get(root + f"/records/{task['id']}?version={approved['version']}").json()[
                "state"
            ]
            == "confirmed"
        )
        assert client.get(root + f"/sources/{source['id']}/original").content.decode() == "原版说明"


def test_device_acceptance_cannot_use_release_checks_and_archived_proof(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        project = client.post(
            "/api/projects",
            json={"name": "设备验收门槛", "source_root": str(services[0].workspace)},
        ).json()["id"]
        store = HandoverStore(app.state.projects)
        source = client.post(
            "/api/handover/sources/capture",
            json={"path": "Program.cs", "actor": "验收人员", "source_project_id": project},
        ).json()
        base = store.create(
            "baseline",
            "测试基线",
            {
                "source_id": source["id"],
                "source_scope": "Program.cs",
                "software_version": "QA1",
                "device": "虚构台架",
                "build": "离线检查",
                "environment": "独立验收",
                "firmware": "不适用",
                "sdk": "不适用",
                "recipe": "不适用",
                "calibration": "不适用",
                "configuration": "测试配置",
            },
            "人",
        )
        from app.modules.handover.application.commands import Action

        def confirm(row):
            return store.action(
                row["id"],
                "confirm",
                Action(version=row["version"], actor="验收人员", opinion="虚构数据下验证业务门槛"),
            )

        base = confirm(base)
        task = store.create(
            "task",
            "设备验收",
            {
                "goal": "复位",
                "acceptance": "设备反馈一致",
                "owner": "验收人员",
                "baseline_id": base["id"],
                "work_status": "accepted",
            },
            "人",
        )
        payload = {
            "task_id": task["id"],
            "baseline_id": base["id"],
            "result": "pass",
            "tester": "验收人员",
            "date": "2026-10-12",
            "environment": "虚构台架",
            "method": "虚构报告用于业务验收",
            "observed": "通过",
            "report": "QA 报告",
        }
        confirm(store.create("verification", "发布检查", {**payload, "layer": "release"}, "人"))
        import pytest

        with pytest.raises(ValueError, match="对应基线"):
            confirm(task)
        device = confirm(
            store.create("verification", "设备记录", {**payload, "layer": "device"}, "人")
        )
        task = confirm(task)
        store.action(
            device["id"],
            "archive",
            Action(version=device["version"], actor="验收人员", opinion="此报告已不适用"),
        )
        current = store.get(task["id"])
        assert current["state"] == "needs_review"
        with pytest.raises(ValueError, match="对应基线"):
            confirm(current)
