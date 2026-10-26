"""源码模拟HTTP入口已暂停；保留独立分析器的只读回归。"""

import hashlib
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.workspace import Workspace

ROOT = Path(__file__).resolve().parents[3]
BASE = "/api/p/independent/action-timing/source-analysis"


@pytest.mark.parametrize("suffix", ["", "/export", "/coverage", "/old-action-id"])
def test_source_http_routes_are_paused_without_constructing_the_analyzer(
    services, monkeypatch, suffix
):
    def forbidden(*args, **kwargs):
        raise AssertionError("暂停的源码模拟不得构造分析器")

    monkeypatch.setattr(SourceTiming, "__init__", forbidden)
    with TestClient(create_app(services[0])) as client:
        response = client.get(BASE + suffix)
        assert response.status_code == 410
        assert response.json()["detail"] == "源码模拟已暂停，请使用动作耗时台账"
    assert not (services[0].data / "cache/action-timing").exists()


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
    wafer_calibration = next(
        row for row in report["rows"] if row["method"] == "OnlyWaferCameraCaib"
    )
    assert wafer_calibration["known_delay_min_ms"] == 75375
    assert wafer_calibration["total_ms"] is None
    fixed_waits = [
        stage["milliseconds"]
        for stage in wafer_calibration["stages"]
        if stage["kind"] == "delay" and not stage["background"] and not stage.get("repeat")
    ]
    assert {delay: fixed_waits.count(delay) for delay in (1000, 2000, 15)} == {
        1000: 25,
        2000: 25,
        15: 25,
    }
    for method, expected_waits in (
        ("StartBondToCamCalibTask", {1414: 2, 1490: 20}),
        ("StartBondToCamCalibTaskWithLocate", {1796: 2, 1875: 20}),
    ):
        calibration = next(
            row
            for row in report["rows"]
            if row["class_name"] == "FrmTestAccuary" and row["method"] == method
        )
        assert calibration["known_delay_min_ms"] >= 5035 and calibration["total_ms"] is None
        lines = Counter(
            stage["line"]
            for stage in calibration["stages"]
            if stage["kind"] == "delay"
            and stage["path"] == calibration["entry"]["path"]
            and not stage["background"]
            and not stage.get("repeat")
        )
        assert {line: lines[line] for line in expected_waits} == expected_waits
    flux = next(row for row in report["rows"] if row["class_name"] == "DipFluxActionNode")
    assert flux["method"] == "DipFluxActionDryRun"
    assert flux["execution_status"] == "unavailable" and flux["total_ms"] is None
    assert "蘸胶空跑动作待验证" in flux["status_reason"]
    wafer_cycle = next(
        row
        for row in report["rows"]
        if row["class_name"] == "WaferSubSystemTask" and row["analysis_unit"] == "single_cycle"
    )
    # 同一编译源码下，这两段条件等待仍须有依据；不能因子调用耗尽图额度消失。
    for line, delay in ((275, 0), (316, 10)):
        assert any(
            stage["kind"] == "delay"
            and stage["path"] == "AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs"
            and stage["line"] == line
            and stage["milliseconds"] == delay
            and not stage["background"]
            for stage in wafer_cycle["stages"]
        )
    repeated_pick = next(
        row
        for row in report["rows"]
        if row["class_name"] == "FrmTest2" and row["method"] == "simpleButton3_Click"
    )
    assert repeated_pick["known_delay_min_ms"] >= 150000 and repeated_pick["total_ms"] is None
    # 100轮各含400ms取片、1000ms放片及100ms停留，不能只保留外层100次。
    fixed_lines = Counter(
        stage["line"]
        for stage in repeated_pick["stages"]
        if stage["kind"] == "delay"
        and stage["path"] == "AKRS.ZX2200/Experiment/TestFunction/FrmTest2.cs"
        and not stage["background"]
        and not stage.get("repeat")
    )
    assert {line: fixed_lines[line] for line in (124, 158, 164, 171, 196, 202)} == dict.fromkeys(
        (124, 158, 164, 171, 196, 202), 100
    )
    assert all(row["entry"]["path"].startswith("AKRS.ZX2200/") for row in report["rows"])
