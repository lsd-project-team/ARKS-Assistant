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
    assert bond["known_delay_min_ms"] == bond["known_delay_max_ms"] == 20
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
