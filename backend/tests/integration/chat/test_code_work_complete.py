"""完整代码工作API：真实账号/项目/文件，编译进程在控制平面测试中替代。"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.code_work.files import PROJECT
from tests.helpers.accounts import login_second, sign_in
from tests.helpers.api_paths import project_api
from tests.helpers.code_work import FILE, make_work


def prepare(client, base=None):
    base = base or project_api(client, "")
    response = client.post(base + "/threads", json={"title": "完整代码工作"})
    assert response.status_code == 201, response.text
    thread = response.json()["id"]
    prefix = base + f"/threads/{thread}/code-work"
    created = client.post(prefix).json()
    assert created["source_pinned"] and created["desktop_flow"]
    assert created["workspace_path"].endswith("source")
    client.put(
        prefix + "/desktop-flow", json={"enabled": False, "revision": created["revision"]}
    ).raise_for_status()
    read = client.get(prefix + "/file", params={"path": FILE}).json()
    response = client.put(
        prefix + "/file",
        json={
            "path": FILE,
            "version": read["version"],
            "content": "class Example { int Value = 9; }",
        },
    )
    assert response.status_code == 200
    return prefix


def process_boundary(arguments, cwd, log, stop, deadline):
    log.write_text("actual process boundary replaced in API test", encoding="utf-8")
    if str(arguments[0]).endswith("VirtualMotionDrivers.Tests.exe"):
        log.write_text("PASS: 16 virtual driver checks", encoding="utf-8")
    if "/p:Configuration=Simulation" in arguments:
        output = Path(
            next(value.split("=", 1)[1] for value in arguments if value.startswith("/p:OutDir="))
        )
        output.mkdir(parents=True)
        (output / f"{PROJECT}.exe").write_bytes(b"api-test-build")
    if "--simulation-self-test" in arguments:
        (Path(arguments[0]).parent / "original-simulation-checks.txt").write_text(
            "PASS: 69 original-project integration checks.", encoding="utf-8"
        )
    return 0


def test_merge_api_requires_current_verified_preview_confirmation_and_can_rollback(
    services, tmp_path, monkeypatch
):
    work, _, original = make_work(services, tmp_path)
    monkeypatch.setattr(
        "app.modules.code_work.environment.CodeEnvironment.compiler",
        lambda self: "fake-msbuild.exe",
    )
    monkeypatch.setattr("app.modules.code_work.runner.execute", process_boundary)
    with TestClient(create_app(services[0])) as client:
        prefix = prepare(client)
        preview_response = client.post(prefix + "/merge/preview", json={"paths": [FILE]})
        assert preview_response.status_code == 200, preview_response.text
        plan = preview_response.json()
        endpoint = prefix + "/merge/" + plan["id"]
        assert not plan["can_apply"] and plan["conflicts"] == []
        assert client.get(prefix).json()["merge_plan_id"] == plan["id"]
        assert (
            client.post(endpoint + "/apply", json={"confirm_target": plan["target"]}).status_code
            == 409
        )
        assert "Value = 1" in (original / "Main/Example.cs").read_text(encoding="utf-8")
        assert client.post(endpoint + "/verify").status_code == 202
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            status = client.get(endpoint).json()
            if status.get("verification", {}).get("status") not in {
                "queued",
                "building",
                "testing",
            }:
                break
            time.sleep(0.02)
        assert status["can_apply"] and status["verification"]["status"] == "passed", status
        assert client.post(endpoint + "/apply", json={"confirm_target": "wrong"}).status_code == 409
        applied = client.post(endpoint + "/apply", json={"confirm_target": plan["target"]})
        assert applied.status_code == 200, applied.text
        assert (
            applied.json()["files"] == [] and applied.json()["applied"][-1]["status"] == "applied"
        )
        assert "Value = 9" in (original / "Main/Example.cs").read_text(encoding="utf-8")
        assert (
            client.post(endpoint + "/apply", json={"confirm_target": plan["target"]}).status_code
            == 409
        )
        report = client.get(
            prefix + "/report",
            params={"plan_id": plan["id"], "job_id": status["verification"]["id"]},
        )
        assert report.status_code == 200 and report.json()["status"] == "passed"
        rolled_back = client.post(endpoint + "/rollback", json={"confirm_target": plan["target"]})
        assert rolled_back.status_code == 200, rolled_back.text
        assert rolled_back.json()["applied"][-1]["status"] == "rolled_back"
        assert "Value = 1" in (original / "Main/Example.cs").read_text(encoding="utf-8")
        assert len(rolled_back.json()["files"]) == 1


@pytest.mark.authentication
def test_normal_user_can_review_but_cannot_write_original_and_other_user_cannot_read(
    services, tmp_path
):
    _, _, original = make_work(services, tmp_path)
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        project = client.post("/api/projects", json={"name": "私人代码副本"})
        assert project.status_code == 201, project.text
        prefix = prepare(client, f"/api/p/{project.json()['id']}")
        plan = client.post(prefix + "/merge/preview", json={}).json()
        endpoint = prefix + "/merge/" + plan["id"]
        for action in ("apply", "rollback"):
            assert (
                client.post(
                    endpoint + "/" + action, json={"confirm_target": plan["target"]}
                ).status_code
                == 403
            )
        assert (
            client.post(
                prefix + "/recovery/0123456789/resolve",
                json={"confirm_target": plan["target"], "versions": {}},
            ).status_code
            == 403
        )
        assert (
            client.put(
                prefix + "/requirement",
                json={
                    "name": "需求",
                    "expectation": "检查业务结果",
                    "code": 'Check(true, "example");',
                },
            ).status_code
            == 200
        )
        sign_in(client, "admin")
        created = client.post(
            "/api/admin/accounts",
            json={
                "username": "second",
                "display_name": "另一账号",
                "role": "user",
                "password": "second-pass-123456",
            },
        )
        assert created.status_code in {200, 201}
        login_second(client)
        requests = [
            ("GET", endpoint, None),
            ("GET", endpoint + "/diff?path=" + FILE, None),
            ("POST", prefix + "/merge/preview", {}),
            ("POST", endpoint + "/verify", {}),
            (
                "PUT",
                prefix + "/requirement",
                {"name": "越权", "expectation": "越权", "code": 'Check(true,"x");'},
            ),
            ("POST", prefix + "/open-directory", {"location": "source"}),
        ]
        for method, url, body in requests:
            assert client.request(method, url, json=body).status_code == 404, (method, url)
        assert "Value = 1" in (original / "Main/Example.cs").read_text(encoding="utf-8")
