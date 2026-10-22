"""源码推算的反例：互斥分支、循环、超时、并发与同名参数不混算。"""

import hashlib

import pytest

from app.modules.action_timing.source_estimator import Estimator
from app.modules.action_timing.source_index import SourceIndex


def analyze(body, declarations="", additional=""):
    source = (
        f"class ActionNode {{}} class Demo : ActionNode {{ {declarations} "
        f"public int DoWork() {{ {body} }} {additional} }}"
    )
    index = SourceIndex(
        [
            {
                "path": "Demo.cs",
                "content": source,
                "version": hashlib.sha256(source.encode()).hexdigest(),
            }
        ]
    )
    return Estimator(index).estimate(index.by_method[("Demo", "DoWork")][0])


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("5 + 7", 12),
        ("5 / 2", 2),
        ("5.0 / 2", 2.5),
        ("(int)2.9", 2),
        ("TimeSpan.FromSeconds(0.02)", 20),
    ],
)
def test_csharp_numeric_and_time_units(expression, expected):
    result = analyze(f"Thread.Sleep({expression}); return 0;")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected


def test_mutually_exclusive_paths_do_not_add_and_early_return_skips_tail():
    result = analyze("if (flag) { Thread.Sleep(10); return 0; } Thread.Sleep(30); return 0;")
    assert result["known_delay_min_ms"] == 10
    assert result["known_delay_max_ms"] == 30


def test_drycycle_prunes_normal_and_offline_paths():
    result = analyze("""
      if (MachineStateModel.GetInstance().MachineWorkMode == MachineWorkModeEnum.OffLineWork)
        { Thread.Sleep(999); return 0; }
      if (MachineStateModel.GetInstance().MachineWorkMode == MachineWorkModeEnum.DryCycle)
        Thread.Sleep(20);
      else Thread.Sleep(800);
      return 0;
    """)
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 20
    assert [stage["milliseconds"] for stage in result["stages"] if stage["kind"] == "delay"] == [20]


def test_short_circuit_does_not_execute_right_side_call():
    result = analyze(
        "if (false && Slow()) Thread.Sleep(50); Thread.Sleep(7); return 0;",
        additional="private bool Slow() { Thread.Sleep(500); return true; }",
    )
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 7


def test_local_assignment_and_switch_use_actual_known_values():
    result = analyze("""
      int delay = 4; delay = 6; delay += 2;
      switch (MachineStateModel.GetInstance().MachineWorkMode) {
        case MachineWorkModeEnum.DryCycle: Thread.Sleep(delay); break;
        default: Thread.Sleep(900); break;
      }
      return 0;
    """)
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 8


def test_explicit_parameter_initializers_are_resolved_by_receiver_type():
    result = analyze(
        "Thread.Sleep(component.PlacementDelay); return 0;",
        "private Component component;",
        "} class Component { public int PlacementDelay {get;set;} = 20; } "
        "class Device { public int PlacementDelay {get;set;} = 100; } class Tail {",
    )
    assert result["known_delay_min_ms"] == 20
    assert result["parameters"][0]["name"] == "Component.PlacementDelay"
    assert result["parameters"][0]["value"] == 20


def test_unknown_parameter_is_not_zero_or_attribute_range():
    result = analyze(
        "Thread.Sleep(component.Delay); return 0;",
        "private Component component;",
        "} class Component { [Range(0,9999)] public int Delay {get;set;} } class Tail {",
    )
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
    assert result["stages"][0]["milliseconds"] is None


def test_failure_guard_retains_cost_of_successful_path():
    result = analyze(
        "if (Signal.WaitStart() == false) return ExcuteResult.Abort; "
        "Thread.Sleep(20); return ExcuteResult.Success;"
    )
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 20
    assert result["total_ms"] is None and result["wait_count"] == 1


def test_timeout_is_not_a_delay_and_polling_is_not_once():
    result = analyze(
        "while (pending) { Thread.Sleep(1); "
        "if (sp.Elapsed.TotalSeconds > 10) return ExcuteResult.Fail; } return 0;"
    )
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
    assert any(
        stage["kind"] == "timeout" and stage["milliseconds"] == 10000 for stage in result["stages"]
    )
    assert any(stage["kind"] == "delay" and stage.get("repeat") for stage in result["stages"])


@pytest.mark.parametrize(
    ("loop", "expected"),
    [
        ("for (int i=0; i<3; i++) { Thread.Sleep(10); }", 30),
        ("for (int i=0; i<0; i++) { Thread.Sleep(10); }", 0),
        ("while (false) { Thread.Sleep(10); }", 0),
        ("do { Thread.Sleep(10); } while (false);", 10),
    ],
)
def test_provable_loop_count(loop, expected):
    result = analyze(loop + " return 0;")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected


def test_background_delegate_is_not_part_of_synchronous_total():
    result = analyze("Task.Run(() => { Thread.Sleep(500); }); Thread.Sleep(7); return 0;")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 7
    assert any(
        stage["kind"] == "delay" and stage["milliseconds"] == 500 and stage["background"]
        for stage in result["stages"]
    )


def test_unknown_motion_preserves_parameters_and_does_not_invent_a_total():
    result = analyze(
        "double speed = 12; axis.SendAbsoluteMoveCommand(target, speed); "
        "MotionService.WaitAxesArrival(axis); Thread.Sleep(5); return 0;"
    )
    assert result["known_delay_min_ms"] == 5 and result["total_ms"] is None
    assert result["motion_count"] == 1 and result["wait_count"] == 1
    motion = next(stage for stage in result["stages"] if stage["kind"] == "motion")
    assert motion["argument_values"] == [None, 12]
    assert any("speed = 12" in source["code"] for source in motion["definitions"])


def test_recursive_call_chain_stays_incomplete():
    result = analyze(
        "Again(); return 0;", additional="private void Again() { Again(); Thread.Sleep(1); }"
    )
    assert result["truncated"] and result["total_ms"] is None


def test_ambiguous_overloads_are_not_bound_by_method_name_only():
    result = analyze(
        "Slow(unknown); return 0;",
        additional=(
            "private void Slow(int v) { Thread.Sleep(10); } "
            "private void Slow(double v) { Thread.Sleep(90); }"
        ),
    )
    assert result["total_ms"] is None
    assert not any(stage["kind"] == "delay" for stage in result["stages"])


def test_omitted_optional_parameter_uses_its_declared_default():
    result = analyze(
        "Delay(); return 0;", additional="private void Delay(int ms = 13) { Thread.Sleep(ms); }"
    )
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 13


def test_branch_mutation_cannot_reuse_a_stale_constant():
    result = analyze("int ms = 20; if (flag) ms = 30; Thread.Sleep(ms); return 0;")
    assert result["known_delay_max_ms"] is None
    assert result["total_ms"] is None


def test_foreach_metadata_does_not_contaminate_explicit_delay():
    result = analyze(
        "foreach (var item in items) { if (item.IsCurrent) break; } Thread.Sleep(20); return 0;"
    )
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 20


def test_failure_only_path_is_not_a_zero_duration_success():
    result = analyze("return ExcuteResult.Abort;")
    assert result["known_delay_min_ms"] is None and result["known_delay_max_ms"] is None
    assert result["total_ms"] is None and not result["complete"]


def test_hardware_stop_is_not_treated_as_a_stopwatch_operation():
    hardware = analyze("axis.Stop(); Thread.Sleep(20); return 0;")
    assert hardware["total_ms"] is None
    assert any(
        stage["kind"] == "call" and "axis.Stop" in stage["code"] for stage in hardware["stages"]
    )
    clock = analyze(
        "Stopwatch sp = new Stopwatch(); sp.Start(); Thread.Sleep(20); sp.Stop(); return 0;"
    )
    assert clock["total_ms"] == 20


def test_wait_timeout_argument_is_an_upper_bound_not_duration():
    result = analyze("signal.WaitOne(5000); Thread.Sleep(20); return 0;")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 20
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "timeout" and stage["milliseconds"] == 5000 for stage in result["stages"]
    )


def test_datetime_timespan_guard_is_reported_as_timeout_only():
    result = analyze(
        "while (pending) { if (DateTime.Now - start > TimeSpan.FromSeconds(10)) "
        "return ExcuteResult.Fail; } Thread.Sleep(20); return 0;"
    )
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 20
    assert any(
        stage["kind"] == "timeout" and stage["milliseconds"] == 10000 for stage in result["stages"]
    )
