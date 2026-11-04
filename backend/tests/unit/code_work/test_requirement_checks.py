"""需求配置、真实报告的完整性规则及重验边界。"""

import json

import pytest

from app.modules.code_work.checks import read_report, validation_version
from tests.helpers.code_work import make_work


def case_body(**extra):
    return {
        "name": "实际需求",
        "expectation": "运行原行为并检查预期",
        "code": 'Check(1 + 1 == 2, "示例断言");',
        **extra,
    }


def test_requirement_versions_freeze_during_repair_and_invalidate_pass(services, tmp_path):
    work, thread, _ = make_work(services, tmp_path)
    first = work.set_requirement(thread, case_body())
    case = first["requirements"][0]
    state_path = work.folder(thread) / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    version = validation_version(state)
    state["verification_attempts"] = {"run": 1}
    state_path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ValueError, match="用例已固定"):
        work.set_requirement(
            thread,
            case_body(id=case["id"], version=case["version"], code='Check(true, "changed");'),
            run_id="run",
        )
    with pytest.raises(ValueError, match="范围已固定"):
        work.set_desktop_flow(thread, False, first["revision"], run_id="run")
    updated = work.set_requirement(
        thread, case_body(id=case["id"], version=case["version"], expectation="调整后的预期")
    )
    assert updated["revision"] == first["revision"] + 1
    assert validation_version(json.loads(state_path.read_text(encoding="utf-8"))) != version
    with pytest.raises(ValueError, match="已更新"):
        work.delete_requirement(thread, case["id"], case["version"])
    latest = updated["requirements"][0]
    assert work.delete_requirement(thread, latest["id"], latest["version"])["requirements"] == []


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [{"id": "case", "status": "passed", "assertions": 0}],
        [{"id": "case", "status": "passed", "assertions": True}],
        [{"id": "wrong", "status": "passed", "assertions": 1}],
        [{"id": "case", "status": "failed", "assertions": 1}],
        ["invalid"],
    ],
)
def test_requirement_report_rejects_empty_incomplete_or_wrong_cases(tmp_path, rows):
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"kind": "requirements", "results": rows}))
    with pytest.raises(ValueError):
        read_report(report, "requirements", {"requirements": [{"id": "case", "enabled": True}]})


def test_requirement_report_requires_exactly_enabled_cases(tmp_path):
    value = {
        "kind": "requirements",
        "results": [{"id": "case", "status": "passed", "assertions": 3}],
    }
    report = tmp_path / "report.json"
    report.write_text(json.dumps(value))
    assert (
        read_report(
            report,
            "requirements",
            {
                "requirements": [
                    {"id": "case", "enabled": True},
                    {"id": "disabled", "enabled": False},
                ]
            },
        )
        == value
    )


async def test_verification_is_limited_to_three_attempts_and_stop_persists(
    services, tmp_path, monkeypatch
):
    work, thread, _ = make_work(services, tmp_path)
    monkeypatch.setattr(work.environment, "compiler", lambda: "fake.exe")

    def fail(arguments, cwd, log, stop, deadline):
        log.write_text("actual failed build boundary")
        return 1

    monkeypatch.setattr("app.modules.code_work.runner.execute", fail)
    for attempt in range(1, 4):
        await work.verify(thread, run_id="repair")
        await work.tasks[thread]
        job = work.status(thread)["verification"]
        assert job["status"] == "failed" and job["attempt"] == attempt
    with pytest.raises(ValueError, match="3次"):
        await work.verify(thread, run_id="repair")
    state_path = work.folder(thread) / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["verification"].update(status="cancelled", run_id="stopped")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ValueError, match="已被停止"):
        await work.verify(thread, run_id="stopped")
    assert len(work.status(thread)["verification_history"]) == 3
    assert work.report(thread, job["id"], "verification.json")
    with pytest.raises(ValueError):
        work.report(thread, job["id"], "../../state.json")
    report_file = work.folder(thread) / "reports" / job["id"] / "verification.json"
    report_file.write_bytes(report_file.read_bytes() + b" ")
    with pytest.raises(ValueError, match="报告被外部修改"):
        work.report(thread, job["id"], "verification.json")


def test_desktop_report_requires_all_steps_and_real_screenshots(tmp_path):
    names = ["loaded", "reset", "start", "pause", "continue", "production", "stop"]
    rows = [
        {
            "id": name,
            "status": "passed",
            "assertions": 1,
            "screenshot": f"code-work-ui-{index:02}.png",
        }
        for index, name in enumerate(names)
    ]
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"kind": "desktop", "results": rows}))
    with pytest.raises(ValueError, match="截图"):
        read_report(report, "desktop", {})
