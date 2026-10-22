"""防止全工程目录遗漏、把后台启动当单轮、或把不可达延时算进去。"""

from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.workspace import Workspace
from tests.unit.test_source_timing_dependencies import analyze


def test_break_and_continue_skip_unreachable_tail():
    stopped = analyze("""class Demo { public int DoWork() {
        while(true) { Thread.Sleep(5); break; Thread.Sleep(999); }
        Thread.Sleep(7); return 0; } }""")
    assert stopped["known_delay_min_ms"] == stopped["known_delay_max_ms"] == 12
    assert not any(stage.get("milliseconds") == 999 for stage in stopped["stages"])
    continued = analyze("""class Demo { public int DoWork() {
        do { Thread.Sleep(3); continue; Thread.Sleep(999); } while(false);
        Thread.Sleep(7); return 0; } }""")
    assert continued["known_delay_min_ms"] == continued["known_delay_max_ms"] == 10


def test_switch_break_does_not_break_enclosing_loop():
    result = analyze("""class Demo { public int DoWork() {
        do { switch(1) { case 1: Thread.Sleep(3); break; }
        Thread.Sleep(7); } while(false); return 0; } }""")
    assert result["total_ms"] == 10


def test_false_predicate_is_a_normal_return_and_throwing_helper_stays_unknown():
    predicate = analyze("""class Demo { public int DoWork() {
        if(Predicate()) Thread.Sleep(999); Thread.Sleep(7); return 0; }
        bool Predicate() { Thread.Sleep(3); return false; } }""")
    assert predicate["total_ms"] == 10
    thrown = analyze("""class Demo { public int DoWork() { Fail(); return 0; }
        void Fail() { throw new Exception(); } }""")
    assert thrown["total_ms"] is None and not thrown["complete"]


def test_non_controller_calibration_initialization_and_ui_are_accounted(tmp_path):
    files = {
        "CalibSystem/Calibrator.cs": (
            "class Calibrator { public void Calib() { Motor(); } "
            "void Motor() { Thread.Sleep(13); } }"
        ),
        "Main/Initialize.cs": "class Startup { public void Init() { Thread.Sleep(7); } }",
        "Controls/Manual.cs": "class Manual { void Click() { new Calibrator().Calib(); } }",
        "Dependency/Package.cs": "class Utility { public void Move() { Thread.Sleep(99); } }",
    }
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    timing = SourceTiming(Workspace(tmp_path))
    report = timing.summary()
    assert {"Calib", "Motor", "Init", "Click"} <= {row["method"] for row in report["rows"]}
    assert report["action_coverage"]["uncatalogued_timing_methods"] == 0
    ledger = timing.coverage()["methods"]
    assert all(row["status"] == "catalogued" for row in ledger)
    assert "methods" not in report["action_coverage"]
    assert (
        next(row for row in report["rows"] if row["method"] == "Calib")["known_delay_min_ms"] == 13
    )


def test_task_service_loop_has_separate_single_cycle(tmp_path):
    path = tmp_path / "TransportSystem/Tasks/TransportTask.cs"
    path.parent.mkdir(parents=True)
    path.write_text(
        """class TransportTask { public void StartDryRun() {
        Task.Run(() => { CommonUtil.SetCurrentThreadName("交接线程");
          while(Signal.WaitStart()) { Thread.Sleep(500); } }); } }""",
        encoding="utf-8",
    )
    report = SourceTiming(Workspace(tmp_path)).summary()
    cycle = next(row for row in report["rows"] if row["analysis_unit"] == "single_cycle")
    launcher = next(row for row in report["rows"] if row["analysis_unit"] == "method")
    assert cycle["name"] == "交接（单轮）" and cycle["primary"]
    assert cycle["total_ms"] == 500
    assert launcher["known_delay_min_ms"] == 0 and not launcher["primary"]
    assert cycle["id"] != launcher["id"]


def test_skipped_loader_and_polling_helpers_are_not_promoted_to_task_cycles(tmp_path):
    path = tmp_path / "TransportSystem/Tasks/LoaderTask.cs"
    path.parent.mkdir(parents=True)
    path.write_text(
        """class LoaderTask { public void Start() {
        if(MachineStateModel.GetInstance().IsDryCycle) return;
        Task.Run(() => { while(Signal.WaitStart()) { Thread.Sleep(500); } }); }
        bool Check() { while(true) { if(ready) break; Thread.Sleep(1); } return true; }
        }""",
        encoding="utf-8",
    )
    rows = SourceTiming(Workspace(tmp_path)).summary()["rows"]
    assert not any(row["analysis_unit"] == "single_cycle" for row in rows)
    loader = next(row for row in rows if row["method"] == "Start")
    assert loader["primary"] and loader["execution_status"] == "skipped"


def test_unknown_concrete_action_does_not_use_empty_virtual_base_body():
    result = analyze("""class ActionNode { public virtual int Work() { return 0; } }
        class Actual : ActionNode { public override int Work() { Thread.Sleep(25); return 0; } }
        class Demo { ActionNode action; public int DoWork() { action.Work(); return 0; } }""")
    assert result["total_ms"] is None
    assert any(stage["kind"] == "unresolved" for stage in result["stages"])
    direct = analyze("""class ActionNode { public virtual int Work() { return 0; } }
        class Actual : ActionNode { public override int Work() { Thread.Sleep(25); return 0; } }
        class Demo { public int DoWork() { new Actual().Work(); return 0; } }""")
    assert direct["total_ms"] == 25


def test_runtime_flags_and_loop_writes_are_not_frozen_to_startup_values():
    runtime = analyze("""class System2RunTimeProvider { public static bool IsNeedDip = false; }
        class Demo { public int DoWork() { if(System2RunTimeProvider.IsNeedDip)
        Thread.Sleep(30); Thread.Sleep(7); return 0; } }""")
    assert (runtime["known_delay_min_ms"], runtime["known_delay_max_ms"]) == (7, 37)
    changed = analyze("""class Demo { public int DoWork() { int delay=10;
        while(pending) { delay=20; } Thread.Sleep(delay); return 0; } }""")
    assert changed["known_delay_max_ms"] is None


def test_recovered_exception_cannot_be_reported_as_zero_or_unavailable():
    result = analyze("""class Demo { public int DoWork() {
        try { throw new Exception(); } catch(Exception) { Thread.Sleep(7); return 0; } } }""")
    assert result["execution_status"] == "partial"
    assert result["known_delay_min_ms"] == 7
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
