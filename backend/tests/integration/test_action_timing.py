"""真实API/SQLite事务、去重、项目权限和C#采集器通路。"""

import csv
import importlib.util
import io
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth.models import Account
from tests.helpers.accounts import sign_in
from tests.helpers.action_timing import raw_package, timing_package, zip_package

ROOT = Path(__file__).resolve().parents[3]
BASE = "/api/p/independent/action-timing"


def test_import_summary_details_pagination_and_exports_survive_restart(services):
    with TestClient(create_app(services[0])) as client:
        result = client.post(BASE + "/imports", content=zip_package())
        assert result.status_code == 201, result.text
        identifier = result.json()["run"]["id"]
        assert result.json()["imported"] == 6 and not result.json()["duplicate"]
        response = client.get(BASE + f"/runs/{identifier}/summary")
        assert response.status_code == 200
        summary = response.json()
        assert summary["covered_actions"] == 5 and summary["data_complete"]
        assert summary["source_kind"] == "collector_test"
        assert all(row["mean_ms"] == 10 and row["valid_count"] == 1 for row in summary["rows"])
        events = client.get(BASE + f"/runs/{identifier}/events?limit=2&offset=2").json()
        assert events["total"] == 5 and len(events["items"]) == 2
        detail = client.get(BASE + f"/runs/{identifier}/events/event-0").json()
        assert detail["event"]["context"]["bond_position"] == "测试焊点"
        assert len(detail["stages"]) == 1 and detail["stages"][0]["stage"] == "移动"
        assert client.get(BASE + f"/runs/{identifier}/events?status=skipped").json()["total"] == 0
        assert client.get(BASE + f"/runs/{identifier}/events?status=invalid").status_code == 422
        exported = client.get(BASE + f"/runs/{identifier}/export").json()
        assert len(exported["events"]) == 6
        csv_response = client.get(BASE + f"/runs/{identifier}/export?format=csv")
        csv_rows = list(csv.reader(io.StringIO(csv_response.text.lstrip("\ufeff"))))
        assert len(csv_rows) == 6 and csv_rows[1][2:4] == ["1", "1"]
    with TestClient(create_app(services[0])) as client:
        assert client.get(BASE + "/runs").json()["total"] == 1
        assert client.get(BASE + f"/runs/{identifier}/summary").json()["covered_actions"] == 5


def test_duplicate_conflict_and_invalid_import_are_atomic(services):
    with TestClient(create_app(services[0])) as client:
        first = client.post(BASE + "/imports", content=raw_package()).json()
        same = timing_package()
        same["events"].reverse()
        duplicate = client.post(BASE + "/imports", content=raw_package(same))
        assert duplicate.status_code == 201 and duplicate.json()["duplicate"]
        assert duplicate.json()["imported"] == 0
        assert duplicate.json()["run"]["id"] == first["run"]["id"]
        changed = timing_package()
        changed["events"][0]["end_ms"] = 9
        assert client.post(BASE + "/imports", content=raw_package(changed)).status_code == 409
        invalid = timing_package()
        invalid["manifest"]["run_id"] = "invalid-new"
        invalid["events"][-1]["parent_id"] = "missing"
        assert client.post(BASE + "/imports", content=raw_package(invalid)).status_code == 422
        assert client.get(BASE + "/runs").json()["total"] == 1
        assert (
            client.get(BASE + f"/runs/{first['run']['id']}/events?kind=stage").json()["total"] == 1
        )


def test_concurrent_imports_and_upload_limit(services, monkeypatch):
    from app.modules.action_timing import router

    with TestClient(create_app(services[0])) as client:
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(
                executor.map(
                    lambda _: client.post(BASE + "/imports", content=raw_package()), range(2)
                )
            )
        assert [response.status_code for response in responses] == [201, 201]
        assert sorted(response.json()["duplicate"] for response in responses) == [False, True]
        assert client.get(BASE + "/runs").json()["total"] == 1
        monkeypatch.setattr(router, "MAX_BYTES", 128)
        assert client.post(BASE + "/imports", content=b"x" * 129).status_code == 413
        assert client.get(BASE + "/runs").json()["total"] == 1


@pytest.mark.authentication
def test_project_and_independent_account_boundaries_cannot_be_forged(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        assert client.get(BASE + "/catalog").status_code == 401
        assert client.get(BASE + "/source-analysis").status_code == 401
        sign_in(client)
        for name in ("timing-a", "timing-b"):
            with app.state.auth.database.session.begin() as session:
                session.add(
                    Account(
                        id=name,
                        username=name,
                        display_name=name,
                        role="user",
                        password_hash=app.state.auth.hasher.hash("test-password-1234"),
                    )
                )

        def login(name):
            response = client.post(
                "/api/auth/login", json={"username": name, "password": "test-password-1234"}
            )
            assert response.status_code == 200
            client.headers["X-Arks-CSRF"] = response.json()["csrf_token"]

        login("timing-a")
        project = client.post("/api/projects", json={"name": "timing-project"}).json()
        scoped = f"/api/p/{project['id']}/action-timing"
        first = client.post(scoped + "/imports", content=raw_package()).json()["run"]["id"]
        independent = client.post(BASE + "/imports", content=raw_package()).json()["run"]["id"]
        assert client.get(BASE + f"/runs/{first}/summary").status_code == 404
        login("timing-b")
        assert client.get(BASE + "/runs").json()["total"] == 0
        assert client.get(BASE + f"/runs/{independent}/summary").status_code == 404
        assert client.get(scoped + f"/runs/{first}/export").status_code == 404
        assert client.get(scoped + "/source-analysis").status_code == 404
        assert client.get(scoped + "/source-analysis/export").status_code == 404
        assert client.post(scoped + "/imports", content=raw_package()).status_code == 404
        own = client.post(BASE + "/imports", content=raw_package())
        assert own.status_code == 201 and not own.json()["duplicate"]
        forged = timing_package()
        forged["manifest"]["owner_id"] = "timing-a"
        assert client.post(BASE + "/imports", content=raw_package(forged)).status_code == 422
        client.headers.pop("X-Arks-CSRF")
        assert client.post(BASE + "/imports", content=raw_package()).status_code == 403


def test_source_preparation_is_read_only_and_preserves_five_existing_paths():
    spec = importlib.util.spec_from_file_location(
        "timing_prepare", ROOT / "backend/tools/ActionTiming/prepare_copy.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = ROOT / "trunk/AKRS.ZX2200"
    before = {
        path: path.read_bytes()
        for path in source.rglob("*.cs")
        if "bin" not in path.parts and "obj" not in path.parts
    }
    edits = module.build_edits(source)
    assert len(edits) == 9
    assert ".Invoke(actionNode.Name" in edits["BondSystem/Tasks/BondTask.cs"]
    assert "return this.PickActionDryRun();" in (
        source / "BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs"
    ).read_text(encoding="utf-8-sig")
    assert all(path.read_bytes() == value for path, value in before.items())
    with pytest.raises(ValueError, match="隔离副本"):
        module.prepare(source, source / "nested")


def test_compiled_csharp_collector_to_import_and_statistics(services, tmp_path):
    candidates = [
        os.environ.get("ARKS_CSC_PATH", ""),
        r"D:\VisualStudio\product\MSBuild\Current\Bin\Roslyn\csc.exe",
        r"D:\VisualStudio\2022\Community\MSBuild\Current\Bin\Roslyn\csc.exe",
    ]
    compiler = next((Path(path) for path in candidates if path and Path(path).is_file()), None)
    if os.name != "nt" or not compiler:
        pytest.skip("需要Windows .NET Framework编译器；不把跳过声称为设备验证")
    exe = tmp_path / "CollectorChecks.exe"
    built = subprocess.run(
        [
            str(compiler),
            "/nologo",
            "/r:System.Web.Extensions.dll",
            f"/out:{exe}",
            str(ROOT / "backend/tools/ActionTiming/Collector.cs"),
            str(ROOT / "backend/tools/ActionTiming/CollectorChecks.cs"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    output = tmp_path / "collected"
    checked = subprocess.run([str(exe), str(output)], capture_output=True, text=True, timeout=60)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "CHECKS_PASSED=" in checked.stdout
    smoke = Path(
        next(
            line.split("=", 1)[1]
            for line in checked.stdout.splitlines()
            if line.startswith("SMOKE=")
        )
    )
    with TestClient(create_app(services[0])) as client:
        for folder in output.iterdir():
            package = {
                "manifest": json.loads((folder / "manifest.json").read_text(encoding="utf-8")),
                "events": [
                    json.loads(line)
                    for line in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines()
                ],
            }
            response = client.post(BASE + "/imports", content=raw_package(package))
            assert response.status_code == 201, response.text
            summary = client.get(BASE + f"/runs/{response.json()['run']['id']}/summary").json()
            if folder == smoke:
                assert summary["covered_actions"] == 5 and summary["action_count"] == 500
                assert all(row["valid_count"] == 100 for row in summary["rows"])
                assert summary["run"]["source_kind"] == "collector_test"
            elif package["manifest"]["state"] == "incomplete":
                assert not summary["data_complete"] and summary["covered_actions"] == 0
