"""程序集版本与重载反例：bool 不是异步开关，未知单位不能编造运动毫秒。"""

import hashlib

import pytest

from app.modules.action_timing.source_estimator import Estimator
from app.modules.action_timing.source_index import SourceIndex
from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.workspace import Workspace


def estimate(body, declarations="Axis axis;", verified=True, extra=""):
    source = (
        "using AKRS.Galaxy2.LogicHardware.Hardwares.MotionControllers; "
        "using AKRS.Galaxy2.Drive.MotionControllerDrive.MotionPara; "
        f"class Demo {{ {declarations} public int DoWork() {{ {body} return 0; }} }} {extra}"
    )
    index = SourceIndex(
        [
            {
                "path": "main.cs",
                "content": source,
                "version": hashlib.sha256(source.encode()).hexdigest(),
            }
        ]
    )
    index.packages = {"AKRS.Galaxy2.LogicHardware": {"verified": verified}}
    return Estimator(index).estimate(index.by_method[("Demo", "DoWork")][0])


def test_absolute_move_bool_false_is_not_async_and_floor_does_not_double_count_motion():
    result = estimate("axis.AbsoluteMove(10, false, 20); Thread.Sleep(7);")
    movement = next(stage for stage in result["stages"] if stage["kind"] == "motion")
    assert "false" in movement["note"] and "重叠" in movement["note"]
    assert movement["motion_model"]["source_fixed_wait_ms"] == 20
    assert movement["motion_model"]["velocity"] == 20
    assert movement["motion_model"]["duration_ms"] is None
    assert result["known_delay_min_ms"] == 7 and result["total_ms"] is None


def test_relative_move_preserves_explicit_profile_values_and_mutation():
    result = estimate("""var para = new MovePara() { TargetPosition=10,
        Vel=5, Acc=20, Dec=30, Jerk=0 }; para.Vel=6; axis.RelativeMove(para);""")
    model = next(stage["motion_model"] for stage in result["stages"] if stage["kind"] == "motion")
    assert (model["distance"], model["velocity"], model["acceleration"], model["deceleration"]) == (
        10,
        6,
        20,
        30,
    )
    assert model["time_unit"] == "unproven" and result["total_ms"] is None


def test_camaxis_and_same_named_source_type_cannot_inherit_ordinary_axis_20ms():
    cam = estimate(
        "axis.AbsoluteMove(new MovePara() { TargetPosition=10, Vel=20 });", "CamAxis axis;"
    )
    model = next(stage["motion_model"] for stage in cam["stages"] if stage["kind"] == "motion")
    assert model["source_fixed_wait_ms"] == 0
    own = estimate(
        "axis.AbsoluteMove(10);",
        extra="class Axis { public void AbsoluteMove(double p) { Thread.Sleep(9); } }",
    )
    assert own["total_ms"] == 9
    assert not any("contract" in stage for stage in own["stages"])
    mismatched = estimate("axis.AbsoluteMove(10, false, 20);", verified=False)
    assert not any("contract" in stage for stage in mismatched["stages"])


def test_sensor_stable_reads_use_intervals_between_reads_and_no_timeout_as_duration():
    sensor = estimate("sensor.CheckStateForNums(true,3,10);", "Sensor sensor;")
    assert (sensor["known_delay_min_ms"], sensor["known_delay_max_ms"]) == (0, 60)
    single = estimate("sensor.CheckStateForNums(true);", "Sensor sensor;")
    assert single["known_delay_max_ms"] == 0 and single["total_ms"] is None
    waited = estimate("sensor.WaitSignal(true,5000,ref cancel);", "Sensor sensor; bool cancel;")
    assert waited["known_delay_min_ms"] == 0
    assert waited["known_delay_max_ms"] is None and waited["total_ms"] is None


def test_binary_changes_invalidate_source_model_and_unverified_contract_is_disabled(tmp_path):
    (tmp_path / "AKRS.ZX2200.csproj").write_text(
        """<Project><ItemGroup>
        <Compile Include="Demo.cs"/><Reference Include="AKRS.Galaxy2.LogicHardware">
        <HintPath>libs/AKRS.Galaxy2.LogicHardware.dll</HintPath></Reference>
        </ItemGroup></Project>""",
        encoding="utf-8",
    )
    (tmp_path / "Demo.cs").write_text(
        "class Demo : ActionNode { public int DoWork() { Thread.Sleep(7); return 0; } }",
        encoding="utf-8",
    )
    dll = tmp_path / "libs/AKRS.Galaxy2.LogicHardware.dll"
    dll.parent.mkdir()
    dll.write_bytes(b"old-version-not-executable")
    timing = SourceTiming(Workspace(tmp_path))
    before = timing.summary()
    assert before["package_contracts"]["AKRS.Galaxy2.LogicHardware"]["verified"] is False
    dll.write_bytes(b"new-version-not-executable")
    after = timing.summary()
    assert before["source_revision"] != after["source_revision"]


def test_unimplemented_syncmove_is_not_reported_as_real_parallel_motion():
    source = """using AKRS.Galaxy2.LogicHardware.Services;
        using AKRS.Galaxy2.LogicHardware.Hardwares.MotionControllers;
        class Demo { CamAxis cam; Axis axis; public int DoWork() {
        MotionService.SyncMove(cam,axis,1.0,2.0,3.0); return 0; } }"""
    index = SourceIndex([{"path": "main.cs", "content": source, "version": "stub"}])
    index.packages = {"AKRS.Galaxy2.LogicHardware": {"verified": True}}
    result = Estimator(index).estimate(index.by_method[("Demo", "DoWork")][0])
    assert result["motion_count"] == 0 and result["total_ms"] == 0
    assert "没有动作实现" in result["stages"][0]["label"]


def test_typed_hardware_query_is_unknown_even_when_its_name_starts_with_get():
    result = estimate("axis.GetRealPosition(); Thread.Sleep(3);")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 3
    assert result["total_ms"] is None
    assert any(stage.get("receiver_type", "").endswith("Axis") for stage in result["stages"])


def test_private_jog_and_query_wrappers_enter_catalog_by_hardware_type(tmp_path):
    (tmp_path / "Demo.cs").write_text(
        """using AKRS.Galaxy2.LogicHardware.Hardwares.MotionControllers;
        class Manual {Axis axis;void Nudge(){axis.Jog(5);}
        void Adjust(){axis.SetVel(3);}double Read(){return axis.GetRealPosition();}}
        class Plain {OtherAxis axis;void Nudge(){axis.Jog(5);}}
        class Factory {void Read(){MotionService.GetInstance();}}""",
        encoding="utf-8",
    )
    rows = SourceTiming(Workspace(tmp_path)).summary()["rows"]
    entries = {(row["class_name"], row["method"]) for row in rows}
    assert {("Manual", "Nudge"), ("Manual", "Adjust"), ("Manual", "Read")} <= entries
    assert ("Plain", "Nudge") not in entries
    assert ("Factory", "Read") not in entries


def test_hardware_type_check_respects_namespace_and_source_implementation():
    source = """using Other;
        class Demo {Axis axis;public int DoWork(){axis.GetRealPosition();return 0;}}"""
    index = SourceIndex([{"path": "main.cs", "content": source, "version": "wrong-import"}])
    result = Estimator(index).estimate(index.by_method[("Demo", "DoWork")][0])
    assert not any(stage.get("receiver_type") for stage in result["stages"])
    own = estimate(
        "axis.GetRealPosition();",
        extra="""class Axis {
        public double GetRealPosition(){Thread.Sleep(9);return 0;}}""",
    )
    assert own["total_ms"] == 9
    assert not any(stage.get("receiver_type") for stage in own["stages"])


def test_source_derived_hardware_and_conditional_access_keep_external_boundary(tmp_path):
    (tmp_path / "Axis.cs").write_text(
        """using AKRS.Galaxy2.LogicHardware.Hardwares.MotionControllers;
        partial class CustomAxis:Axis {}""",
        encoding="utf-8",
    )
    (tmp_path / "Axis.Other.cs").write_text("partial class CustomAxis {}", encoding="utf-8")
    (tmp_path / "Manual.cs").write_text(
        "class Manual {CustomAxis axis;void Nudge(){axis?.Jog(5);}}", encoding="utf-8"
    )
    rows = SourceTiming(Workspace(tmp_path)).report()["rows"]
    row = next(row for row in rows if row["class_name"] == "Manual")
    assert row["motion_count"] == 1 and row["total_ms"] is None
    assert any(stage.get("receiver_type", "").endswith(".Axis") for stage in row["stages"])


def test_hardware_property_type_uses_declaration_imports_in_another_file(tmp_path):
    (tmp_path / "Device.cs").write_text(
        """using AKRS.Galaxy2.LogicHardware.Hardwares.MotionControllers;
        class Device {public Axis AxisX {get;} public Sensor Pressure;}""",
        encoding="utf-8",
    )
    (tmp_path / "Manual.cs").write_text(
        """class Manual {Device device;
        double Read(){return device.AxisX.GetRealPosition();}
        void Check(){device.Pressure.ReadTxPDO(0,1);}}""",
        encoding="utf-8",
    )
    rows = SourceTiming(Workspace(tmp_path)).report()["rows"]
    assert {("Manual", "Read"), ("Manual", "Check")} <= {
        (row["class_name"], row["method"]) for row in rows
    }
    assert all(row["total_ms"] is None for row in rows if row["class_name"] == "Manual")


def test_verified_contract_uses_external_property_declaration_type():
    index = SourceIndex(
        [
            {
                "path": "Device.cs",
                "content": """using AKRS.Galaxy2.LogicHardware.Hardwares.MotionControllers;
        class Device {public Axis AxisX {get;}}""",
                "version": "device",
            },
            {
                "path": "Demo.cs",
                "content": """class Demo {Device device;public int DoWork(){
        device.AxisX.AbsoluteMove(10,false,20);return 0;}}""",
                "version": "caller",
            },
        ]
    )
    index.packages = {"AKRS.Galaxy2.LogicHardware": {"verified": True}}
    result = Estimator(index).estimate(index.by_method[("Demo", "DoWork")][0])
    stage = next(stage for stage in result["stages"] if stage["kind"] == "motion")
    assert "contract" in stage and stage["motion_model"]["source_fixed_wait_ms"] == 20


@pytest.mark.parametrize(
    "prefix,suffix,matched",
    [
        (
            "namespace AKRS.ZX2200; using Galaxy2.LogicHardware.Hardwares.MotionControllers;",
            "",
            True,
        ),
        (
            "using Galaxy2.LogicHardware.Hardwares.MotionControllers; namespace AKRS.ZX2200;",
            "",
            False,
        ),
        (
            "namespace AKRS.ZX2200 { using Galaxy2.LogicHardware.Hardwares.MotionControllers;",
            "}",
            True,
        ),
    ],
)
def test_relative_namespace_import_obeys_its_csharp_scope(prefix, suffix, matched):
    source = (
        prefix
        + """class Demo {Axis axis;public int DoWork(){
        axis.AbsoluteMove(10,false,20);return 0;}}"""
        + suffix
    )
    index = SourceIndex([{"path": "main.cs", "content": source, "version": "relative"}])
    index.packages = {"AKRS.Galaxy2.LogicHardware": {"verified": True}}
    result = Estimator(index).estimate(index.by_method[("Demo", "DoWork")][0])
    assert any("contract" in stage for stage in result["stages"]) is matched
