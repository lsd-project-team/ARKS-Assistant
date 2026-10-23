"""直接读源码的真实API、权限、缓存失效与ZX2200参数依据。"""

import csv
import hashlib
import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.workspace import Workspace

ROOT = Path(__file__).resolve().parents[3]
BASE = "/api/p/independent/action-timing/source-analysis"


def test_page_data_is_available_without_import_and_changes_with_source(services):
    path = services[2].root / "Demo.cs"
    path.write_text(
        "class Demo : ActionNode { public int DoWork() { Thread.Sleep(12); return 0; } }",
        encoding="utf-8",
    )
    with TestClient(create_app(services[0])) as client:
        response = client.get(BASE)
        assert response.status_code == 200, response.text
        first = response.json()
        row = next(row for row in first["rows"] if row["class_name"] == "Demo")
        assert first["basis"] == "source_defaults" and first["mode"] == "DryCycle"
        assert row["known_delay_min_ms"] == row["known_delay_max_ms"] == 12
        assert "stages" not in row
        coverage = client.get(BASE + "/coverage")
        assert coverage.status_code == 200
        assert coverage.json()["source_revision"] == first["source_revision"]
        assert coverage.json()["uncatalogued_timing_methods"] == 0
        assert any(
            item["method"] == "Demo.DoWork" and item["status"] == "catalogued"
            for item in coverage.json()["methods"]
        )
        detail = client.get(BASE + "/" + row["id"])
        assert detail.status_code == 200
        assert detail.json()["stages"][0]["path"] == "Demo.cs"
        assert detail.json()["stages"][0]["milliseconds"] == 12
        assert client.get("/api/p/independent/action-timing/runs").json()["total"] == 0
        path.write_text(
            path.read_text(encoding="utf-8").replace("Sleep(12)", "Sleep(21)"), encoding="utf-8"
        )
        updated = client.get(BASE).json()
        assert updated["source_revision"] != first["source_revision"]
        assert updated["rows"][0]["known_delay_min_ms"] == 21
        exported = client.get(BASE + "/export")
        assert exported.status_code == 200
        rows = list(csv.reader(io.StringIO(exported.text.lstrip("\ufeff"))))
        assert rows[1][3:5] == ["21", "21"]
        assert rows[1][-1] == "源码默认值推算，非现场实测"
        assert client.get(BASE + "/missing").status_code == 404


def test_source_api_keeps_per_item_timing_without_requiring_hardware_or_import(services):
    (services[2].root / "Demo.cs").write_text(
        "using System.Collections.Generic;class Demo : ActionNode {List<int> items;"
        "public int DoWork(){items.ForEach(n=>Thread.Sleep(7));return 0;}}",
        encoding="utf-8",
    )
    with TestClient(create_app(services[0])) as client:
        response = client.get(BASE)
        assert response.status_code == 200
        row = next(row for row in response.json()["rows"] if row["class_name"] == "Demo")
        assert row["known_delay_min_ms"] == 0 and row["known_delay_max_ms"] is None
        assert row["total_ms"] is None
        assert row["per_item_timing"] == [{"element_type": "int", "min_ms": 7, "max_ms": 7}]
        assert "stages" not in row
        detail = client.get(BASE + "/" + row["id"])
        assert detail.status_code == 200
        assert detail.json()["per_item_timing"] == row["per_item_timing"]
        assert any(
            stage["kind"] == "delay" and stage["milliseconds"] == 7 and stage["repeat"]
            for stage in detail.json()["stages"]
        )
        assert client.get("/api/p/independent/action-timing/runs").json()["total"] == 0


def test_source_api_computes_filtered_and_materialized_callbacks_without_import(services):
    (services[2].root / "Demo.cs").write_text(
        "using System.Collections.Generic;using System.Linq;class Demo:ActionNode{"
        "public int DoWork(){new List<int>{1,2,3}.FindAll(n=>{Thread.Sleep(2);return n>1;})"
        ".ToList().ForEach(n=>Thread.Sleep(n));return 0;}}",
        encoding="utf-8",
    )
    with TestClient(create_app(services[0])) as client:
        response = client.get(BASE)
        assert response.status_code == 200
        row = next(row for row in response.json()["rows"] if row["class_name"] == "Demo")
        assert row["total_ms"] == row["known_delay_min_ms"] == row["known_delay_max_ms"] == 11
        detail = client.get(BASE + "/" + row["id"])
        assert detail.status_code == 200
        assert sum(s["kind"] == "delay" for s in detail.json()["stages"]) == 5
        assert client.get("/api/p/independent/action-timing/runs").json()["total"] == 0


def test_source_api_consumes_queries_and_streams_foreach_without_import(services):
    (services[2].root / "Demo.cs").write_text(
        "using System.Linq;class Demo:ActionNode{public int DoWork(){"
        "Thread.Sleep(new[]{1,2,3}.Count(n=>{Thread.Sleep(2);return n>1;}));"
        "foreach(var n in new[]{2,3}.Select(n=>{Thread.Sleep(1);return n;}))"
        "{Thread.Sleep(n);break;}return 0;}}",
        encoding="utf-8",
    )
    with TestClient(create_app(services[0])) as client:
        response = client.get(BASE)
        assert response.status_code == 200
        row = next(row for row in response.json()["rows"] if row["class_name"] == "Demo")
        assert row["total_ms"] == row["known_delay_min_ms"] == row["known_delay_max_ms"] == 11
        detail = client.get(BASE + "/" + row["id"])
        assert detail.status_code == 200
        assert sum(s["kind"] == "delay" for s in detail.json()["stages"]) == 6
        assert client.get("/api/p/independent/action-timing/runs").json()["total"] == 0


def test_main_zx_project_is_not_mixed_with_output_copy(tmp_path):
    original = tmp_path / "AKRS.ZX2200"
    copied = tmp_path / "output/AKRS.ZX2200"
    for directory, delay in [(original, 20), (copied, 900)]:
        directory.mkdir(parents=True)
        (directory / "AKRS.ZX2200.csproj").write_text("<Project/>", encoding="utf-8")
        (directory / "Demo.cs").write_text(
            "class Demo : ActionNode { public int DoWork() { "
            f"Thread.Sleep({delay}); return 0; " + "} }",
            encoding="utf-8",
        )
    report = SourceTiming(Workspace(tmp_path)).summary()
    assert len(report["rows"]) == 1
    assert report["rows"][0]["known_delay_min_ms"] == 20
    assert report["rows"][0]["entry"]["path"] == "AKRS.ZX2200/Demo.cs"


def test_actual_zx_source_delays_and_entry_coverage_are_read_only():
    root = ROOT / "trunk/AKRS.ZX2200"
    workspace = Workspace(root)
    before = {
        workspace.relative(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in workspace.files()
        if path.suffix == ".cs"
    }
    service = SourceTiming(workspace)
    report = service.report()
    rows = {
        row["class_name"]: row for row in report["rows"] if row["kind"] in {"node", "placeholder"}
    }
    uplook = rows["UpLookCorrectionActionNode"]
    assert uplook["method"] == "UplookActionDryRun"
    assert uplook["known_delay_min_ms"] == 20 and uplook["known_delay_max_ms"] == 40
    assert uplook["total_ms"] is None and uplook["motion_count"] > 0
    bond = rows["BondActionNode"]
    # 固定放置停留仍为20ms；末尾的公开刷新委托未绑定，不能再断言软件等待上界。
    assert bond["known_delay_min_ms"] == 20 and bond["known_delay_max_ms"] is None
    assert any(
        stage["kind"] == "delay"
        and stage["milliseconds"] == 20
        and stage["code"] == "DelayHelper.Delay(component.PlacementDelay)"
        for stage in bond["stages"]
    )
    assert any(
        stage["kind"] == "unresolved"
        and stage["label"] == "委托目标为空或尚未绑定"
        and stage["code"] == "UcMainSystem.ReFreshSystem2TuAction()"
        and stage["path"].endswith("BondActionNode.MoveHelper.cs")
        for stage in bond["stages"]
    )
    assert any(
        param["name"] == "BaseCarrierConfig.PlacementDelay" and param["value"] == 20
        for param in bond["parameters"]
    )
    assert rows["PickActionNode"]["wait_count"] > 0
    assert rows["S2EpoxyDefectActionNode"]["kind"] == "placeholder"
    assert rows["S1CarrierVisionActionNode"]["name"] == "S1 载具定位"
    assert rows["S1TransportIdentityActionNode"]["name"] == "S1 载具身份识别"
    assert {
        "S1TransportIdentityActionNode",
        "S1ModuleMeasureHeightActionNode",
        "S2CarrierVisionActionNode",
        "DipFluxActionNode",
        "SubstrateCameraCorrectionActionNode",
    } <= rows.keys()
    assert any(
        row["class_name"] == "TransportController" and row["method"] == "TransferDispenseToBond"
        for row in report["rows"]
    )
    assert any(
        row["class_name"] == "Block" and row["method"] == "NextDie" for row in report["rows"]
    )
    assert len(report["rows"]) == len({row["id"] for row in report["rows"]})
    assert all(
        hashlib.sha256((root / path).read_bytes()).hexdigest() == version
        for path, version in before.items()
    )


def test_whole_trunk_follows_package_signal_source_without_exposing_packages_as_actions():
    service = SourceTiming(Workspace(ROOT / "trunk"))
    report = service.report()
    self_check = next(
        row
        for row in report["rows"]
        if row["class_name"] == "Machine" and row["method"] == "SelfCheck"
    )
    assert self_check["total_ms"] is None
    assert any(
        item["element_type"] == "Light" and item["min_ms"] == 2000
        for item in self_check["per_item_timing"]
    )
    assert any(
        stage["kind"] == "delay"
        and stage["milliseconds"] == 2000
        and stage["repeat"]
        and stage["path"].endswith("Machine.SelfCheck.cs")
        for stage in self_check["stages"]
    )
    assert {"AKRS.ZX2200", "AKRS.Galaxy2.Machine", "AKRS.Galaxy2.Dispense"} <= {
        item["assembly"] for item in report["source_projects"]
    }
    paths = {item["path"] for item in service.loaded_scope.documents}
    assert "AKRS.Galaxy2.Machine/Models/Signal.cs" in paths
    assert any("/CalibSystem/" in path for path in paths)
    pick = next(row for row in report["rows"] if row["class_name"] == "PickActionNode")
    assert pick["known_delay_min_ms"] >= 5 and pick["total_ms"] is None
    assert any(
        stage["path"] == "AKRS.Galaxy2.Machine/Models/Signal.cs"
        and stage["kind"] == "delay"
        and stage["milliseconds"] == 5
        for stage in pick["stages"]
    )
    flux = next(row for row in report["rows"] if row["class_name"] == "DipFluxActionNode")
    assert flux["method"] == "DipFluxActionDryRun"
    assert flux["execution_status"] == "unavailable" and flux["total_ms"] is None
    assert "蘸胶空跑动作待验证" in flux["status_reason"]
    assert all(row["entry"]["path"].startswith("AKRS.ZX2200/") for row in report["rows"])
