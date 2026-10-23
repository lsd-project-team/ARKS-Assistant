"""旧式异步委托按发起与EndInvoke完成边界建模，不执行.NET或设备程序。"""

import json
from pathlib import Path

import pytest

from tests.unit.test_source_timing_dependencies import analyze


def delays(result):
    return [stage for stage in result["stages"] if stage["kind"] == "delay"]


def test_begin_exposes_background_body_without_charging_the_caller():
    result = analyze("""using System;class Demo {public int DoWork(){
        Action action=()=>Thread.Sleep(20);var result=action.BeginInvoke(null,"succeed");
        Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] == 3
    assert [(stage["milliseconds"], stage["background"]) for stage in delays(result)] == [
        (20, True),
        (3, False),
    ]
    json.dumps(result)


@pytest.mark.parametrize(("elapsed", "expected"), [(0, 20), (5, 20), (30, 30)])
def test_end_waits_only_for_the_remaining_delegate_time(elapsed, expected):
    result = analyze(f"""using System;class Demo {{public int DoWork(){{
        Action action=()=>Thread.Sleep(20);var result=action.BeginInvoke(null,"succeed");
        Thread.Sleep({elapsed});action.EndInvoke(result);return 0;}}}}""")
    assert result["total_ms"] == expected
    assert not next(stage for stage in delays(result) if stage["milliseconds"] == 20)["background"]


def test_independent_async_delegates_overlap_instead_of_summing_their_bodies():
    result = analyze("""using System;class Demo {public int DoWork(){
        Action first=()=>Thread.Sleep(20),second=()=>Thread.Sleep(30);
        var a=first.BeginInvoke(null,null);var b=second.BeginInvoke(null,null);
        Thread.Sleep(5);first.EndInvoke(a);second.EndInvoke(b);return 0;}}""")
    assert result["total_ms"] == 30


def test_unknown_intervening_delay_keeps_the_completed_target_time_as_a_lower_bound():
    result = analyze("""using System;class Demo {int unknown;public int DoWork(){
        Action action=()=>Thread.Sleep(20);var pending=action.BeginInvoke(null,null);
        Thread.Sleep(unknown);action.EndInvoke(pending);return 0;}}""")
    assert result["known_delay_min_ms"] == 20
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None


def test_joining_two_partial_targets_keeps_the_later_known_completion_floor():
    result = analyze("""using System;class Demo {int unknown;public int DoWork(){
        Action first=()=>{Thread.Sleep(unknown);Thread.Sleep(20);};
        Action second=()=>{Thread.Sleep(unknown);Thread.Sleep(30);};
        var a=first.BeginInvoke(null,null);var b=second.BeginInvoke(null,null);
        first.EndInvoke(a);second.EndInvoke(b);return 0;}}""")
    assert result["known_delay_min_ms"] == 30
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None


def test_typed_argument_is_saved_before_later_caller_writes():
    result = analyze("""using System;class Demo {public int DoWork(){int ms=20;
        Action<int> action=n=>Thread.Sleep(n);var result=action.BeginInvoke(ms,null,null);
        ms=999;action.EndInvoke(result);return 0;}}""")
    assert result["total_ms"] == 20


def test_later_argument_cannot_replace_the_already_evaluated_delegate():
    result = analyze("""using System;class Demo {Action action;
        object Change(){action=()=>Thread.Sleep(999);return null;}
        public int DoWork(){action=()=>Thread.Sleep(20);Action original=action;
        var result=action.BeginInvoke(null,Change());original.EndInvoke(result);return 0;}}""")
    assert result["total_ms"] == 20
    assert not any(stage["milliseconds"] == 999 for stage in delays(result))


def test_field_handle_and_method_group_survive_source_helper_boundaries():
    result = analyze("""using System;class Demo {Action action;IAsyncResult pending;
        void Move(){Thread.Sleep(20);}
        void Start(){action=Move;pending=action.BeginInvoke(null,"succeed");}
        void Finish(){action.EndInvoke(pending);}
        public int DoWork(){Start();Thread.Sleep(5);Finish();return 0;}}""")
    assert result["total_ms"] == 20


def test_returned_handle_and_alias_keep_their_original_completion_boundary():
    result = analyze("""using System;class Demo {Action action;
        IAsyncResult Start(){action=()=>Thread.Sleep(20);return action.BeginInvoke(null,null);}
        void Finish(IAsyncResult value){action.EndInvoke(value);}
        public int DoWork(){var pending=Start();var alias=pending;
        Thread.Sleep(5);Finish(alias);return 0;}}""")
    assert result["total_ms"] == 20


def test_end_returns_a_func_value_for_subsequent_source_calculation():
    result = analyze("""using System;class Demo {public int DoWork(){
        Func<int> action=()=>{Thread.Sleep(2);return 7;};
        var pending=action.BeginInvoke(null,null);int ms=action.EndInvoke(pending);
        Thread.Sleep(ms);return 0;}}""")
    assert result["total_ms"] == 9


def test_end_does_not_join_an_unawaited_task_created_inside_the_target():
    result = analyze("""using System;class Demo {public int DoWork(){
        Action action=()=>{Task.Run(()=>Thread.Sleep(999));Thread.Sleep(20);};
        var pending=action.BeginInvoke(null,null);action.EndInvoke(pending);
        Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] == 23
    assert next(stage for stage in delays(result) if stage["milliseconds"] == 999)["background"]


def test_async_action_end_waits_for_the_synchronous_prefix_only():
    result = analyze("""using System;class Demo {public int DoWork(){
        Action action=async()=>{Thread.Sleep(3);await Task.Delay(999);};
        var pending=action.BeginInvoke(null,null);action.EndInvoke(pending);
        Thread.Sleep(5);return 0;}}""")
    assert result["total_ms"] == 8
    assert next(stage for stage in delays(result) if stage["milliseconds"] == 999)["background"]


def test_func_task_is_returned_by_end_and_joined_only_by_explicit_wait():
    result = analyze("""using System;class Demo {public int DoWork(){
        Func<Task> action=async()=>{Thread.Sleep(3);await Task.Delay(20);};
        var pending=action.BeginInvoke(null,null);var task=action.EndInvoke(pending);
        Thread.Sleep(5);task.Wait();return 0;}}""")
    assert result["total_ms"] == 23


@pytest.mark.parametrize(
    "tail",
    [
        "other.EndInvoke(pending);",
        "action.EndInvoke(new object());",
        "action.EndInvoke(pending);action.EndInvoke(pending);",
    ],
)
def test_unmatched_unknown_or_reused_handles_do_not_claim_known_completion(tail):
    result = analyze(f"""using System;class Demo {{public int DoWork(){{
        Action action=()=>Thread.Sleep(20),other=()=>Thread.Sleep(999);
        var pending=action.BeginInvoke(null,null);{tail}return 0;}}}}""")
    assert result["total_ms"] is None
    assert any(stage["kind"] == "unresolved" and stage.get("apm") for stage in result["stages"])
    assert not any(stage["milliseconds"] == 999 for stage in delays(result))


def test_queued_mutable_capture_is_not_frozen_as_twenty_or_nine_hundred_ninety_nine():
    result = analyze("""using System;class Demo {public int DoWork(){int ms=20;
        Action action=()=>Thread.Sleep(ms);var pending=action.BeginInvoke(null,null);
        ms=999;action.EndInvoke(pending);return 0;}}""")
    assert result["total_ms"] is None
    assert all(stage["milliseconds"] not in {20, 999} for stage in delays(result))


def test_queued_constant_capture_remains_calculable():
    result = analyze("""using System;class Demo {public int DoWork(){const int ms=20;
        Action action=()=>Thread.Sleep(ms);var pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}""")
    assert result["total_ms"] == 20


def test_background_shared_write_invalidates_old_caller_value():
    result = analyze("""using System;class Demo {public int DoWork(){int ms=5;
        Action action=()=>ms=7;action.BeginInvoke(null,null);Thread.Sleep(ms);return 0;}}""")
    assert result["total_ms"] is None
    assert [stage["milliseconds"] for stage in delays(result)] == [None]


def test_background_read_does_not_invalidate_unchanged_caller_value():
    result = analyze("""using System;class Demo {public int DoWork(){int ms=20;
        Action action=()=>Thread.Sleep(ms);action.BeginInvoke(null,null);
        Thread.Sleep(ms);return 0;}}""")
    assert result["total_ms"] == 20


@pytest.mark.parametrize(
    "declaration,invocation",
    [
        ("Action action=()=>Thread.Sleep(999);", "action.BeginInvoke(7,null,null);"),
        ("Action<bool> action=n=>Thread.Sleep(999);", "action.BeginInvoke(7,null,null);"),
        ("Action action=()=>Thread.Sleep(999);", "action.BeginInvoke(callback,null);"),
    ],
)
def test_unbound_signature_or_completion_callback_keeps_an_explicit_boundary(
    declaration, invocation
):
    result = analyze(f"""using System;class Demo {{AsyncCallback callback;
        public int DoWork(){{{declaration}{invocation}return 0;}}}}""")
    assert result["total_ms"] is None
    assert any(stage["kind"] == "unresolved" and stage.get("apm") for stage in result["stages"])


def test_source_types_with_same_method_names_keep_their_own_implementation():
    result = analyze("""class Action {
        public object BeginInvoke(object callback,object state){Thread.Sleep(7);return null;}
        public void EndInvoke(object value){Thread.Sleep(11);}}
        class Demo {public int DoWork(){var action=new Action();
        var pending=action.BeginInvoke(null,null);action.EndInvoke(pending);return 0;}}""")
    assert result["total_ms"] == 18
    assert not any(stage.get("apm") for stage in result["stages"])


def test_typed_member_assignment_retains_signature_for_other_delegate_invocation_paths():
    result = analyze("""using System;class Demo {Action<int> action;
        void Sleep(int ms){Thread.Sleep(ms);}
        public int DoWork(){action=Sleep;action.DynamicInvoke(7);return 0;}}""")
    assert result["total_ms"] == 7


@pytest.fixture(scope="module")
def real_wafer_index():
    from app.modules.action_timing.source_hardware import bind_packages
    from app.modules.action_timing.source_index import SourceIndex
    from app.modules.action_timing.source_scope import load_scope
    from app.modules.source_analysis.workspace import Workspace

    scope = load_scope(Workspace(Path(__file__).resolve().parents[3] / "trunk"))
    index = SourceIndex(scope.documents, scope.declarations)
    index.packages = bind_packages(scope.references)
    return index


@pytest.mark.parametrize(
    ("method", "expected"), [("PreChangeTablet", 2), ("AsyncMoveMagazineToSafePosition", 1)]
)
def test_actual_wafer_controller_binds_all_three_field_delegate_starts(
    real_wafer_index, method, expected
):
    from app.modules.action_timing.source_estimator import Estimator

    target = real_wafer_index.by_method[("WaferTableController", method)][0]
    result = Estimator(real_wafer_index).estimate(target)
    started = [
        stage
        for stage in result["stages"]
        if stage.get("apm") and stage.get("operation") == "begin"
    ]
    assert len(started) == expected
    assert all(stage["path"] == target.unit.path and stage["background"] for stage in started)
    assert any(
        stage["background"] and stage["kind"] in {"motion", "delay"} for stage in result["stages"]
    )
    assert result["total_ms"] is None
    json.dumps(result)


def test_an_async_target_has_its_own_budget_after_the_caller_reaches_the_limit():
    result = analyze("""using System;class Demo {Action action;
        void Empty(){}void Fill(){for(int n=0;n<130;n++)Empty();}
        public int DoWork(){Fill();action=()=>Thread.Sleep(7);
        var pending=action.BeginInvoke(null,null);action.EndInvoke(pending);return 0;}}""")
    assert result["truncated"]
    assert any(stage["milliseconds"] == 7 and not stage["background"] for stage in delays(result))
    assert any(stage.get("operation") == "end" for stage in result["stages"])


def test_actual_typed_expansion_start_and_end_expand_the_original_motion_body(real_wafer_index):
    from app.modules.action_timing.source_estimator import Estimator

    target = real_wafer_index.by_method[("WaferTableController", "RemoveWaferFromSlot")][0]
    result = Estimator(real_wafer_index).estimate(target)
    assert any(
        stage.get("operation") == "begin" and stage["line"] == 1171 for stage in result["stages"]
    )
    assert any(
        stage.get("operation") == "end" and stage["line"] == 1180 for stage in result["stages"]
    )
    assert any(
        stage["method"] == "WaferTableController.MoveExpandAxisZToG0Pos"
        and stage["line"] == 1534
        and stage["kind"] == "motion"
        and not stage["background"]
        for stage in result["stages"]
    )
    assert result["total_ms"] is None


def test_target_budget_limits_remain_in_force_and_uncaptured_local_handle_can_still_be_joined():
    result = analyze("""using System;class Demo {
        void Empty(){}void Hidden(){Thread.Sleep(999);}
        void Move(){for(int n=0;n<130;n++)Empty();Hidden();Thread.Sleep(7);}
        public int DoWork(){Action action=Move;var pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}""")
    assert result["truncated"] and result["total_ms"] is None
    assert any(stage.get("operation") == "end" for stage in result["stages"])
    assert not any(stage["milliseconds"] == 999 for stage in delays(result))


def test_infinite_async_rescheduling_is_still_bounded():
    result = analyze("""using System;class Demo {void Launch(){
        Action action=()=>Launch();action.BeginInvoke(null,null);}
        public int DoWork(){Launch();return 0;}}""")
    assert result["truncated"]
    assert len(result["stages"]) < 40


def test_a_pattern_variable_property_has_the_static_type_needed_by_begin_arguments():
    result = analyze("""using System;class Box{public int Delay;}
        class Demo {public int DoWork(object input){if(input is Box wt){
        Action<int> action=n=>Thread.Sleep(n);var pending=action.BeginInvoke(wt.Delay,null,null);
        action.EndInvoke(pending);}return 0;}}""")
    assert any(stage.get("operation") == "begin" for stage in result["stages"])
    assert any(stage.get("operation") == "end" for stage in result["stages"])


def test_outer_pattern_type_is_retained_inside_an_async_callback():
    result = analyze("""using System;class Box{public void Work(){Thread.Sleep(7);}}
        class Demo {public int DoWork(object input){if(input is Box wt){
        Action action=()=>wt.Work();var pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);}return 0;}}""")
    assert any(stage["milliseconds"] == 7 for stage in delays(result))


def test_a_pattern_in_another_block_does_not_replace_the_same_named_field():
    result = analyze("""class Box{public void Work(){Thread.Sleep(7);}}
        class Other{public void Work(){Thread.Sleep(11);}}
        class Demo {Other wt=new Other();public int DoWork(object input){
        {if(input is Box wt)wt.Work();}wt.Work();return 0;}}""")
    assert result["known_delay_min_ms"] == 11 and result["known_delay_max_ms"] == 18


def test_a_pattern_inside_a_condition_lambda_does_not_shadow_the_callers_field():
    result = analyze("""using System;class Box{public void Work(){Thread.Sleep(7);}}
        class Other{public void Work(){Thread.Sleep(11);}}
        class Demo {Other wt=new Other();bool Check(Func<bool> callback){return true;}
        public int DoWork(object input){if(Check(()=>input is Box wt))wt.Work();return 0;}}""")
    assert result["total_ms"] == 11
