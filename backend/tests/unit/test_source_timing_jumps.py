"""标签是执行入口；跳转不能漏算重试或继续累加不可达尾部。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Start:Thread.Sleep(5);", 5),
        ("goto End;Thread.Sleep(999);End:Thread.Sleep(7);", 7),
        ("int i=0;Again:Thread.Sleep(2);i++;if(i<3)goto Again;Thread.Sleep(7);", 13),
        ("int i=0;Again:Thread.Sleep(2);if(++i<3){goto Again;}Thread.Sleep(i);", 9),
        ("int i=0;Again:Thread.Sleep(2);if(++i<3){goto Again;}else return 0;Thread.Sleep(999);", 6),
        (
            "for(int i=0;i<5;i++){Thread.Sleep(2);if(i==2)goto End;}"
            "Thread.Sleep(999);End:Thread.Sleep(7);",
            13,
        ),
        (
            "int i=0;while(i<5){Thread.Sleep(2);if(i++==2)goto End;}"
            "Thread.Sleep(999);End:Thread.Sleep(7);",
            13,
        ),
        (
            "switch(1){case 1:Thread.Sleep(2);goto End;default:Thread.Sleep(999);break;}"
            "Thread.Sleep(999);End:Thread.Sleep(7);",
            9,
        ),
        (
            "try{Thread.Sleep(3);goto End;}finally{Thread.Sleep(5);}"
            "Thread.Sleep(999);End:Thread.Sleep(7);",
            15,
        ),
        (
            "int i=0;try{Again:Thread.Sleep(2);if(++i<3)goto Again;}"
            "finally{Thread.Sleep(5);}Thread.Sleep(7);",
            18,
        ),
        (
            "int delay=1;{delay=7;goto End;Thread.Sleep(999);}"
            "Thread.Sleep(999);End:Thread.Sleep(delay);",
            7,
        ),
    ],
)
def test_label_execution_jumps_and_unreachable_paths(body, expected):
    result = analyze(f"class Demo {{public int DoWork(){{{body}return 0;}}}}")
    assert result["total_ms"] == expected
    assert not any(s.get("milliseconds") == 999 for s in result["stages"])


def test_unknown_retry_condition_with_a_known_counter_guard_has_a_finite_delay_range():
    result = analyze("""class Demo {bool retry;public int DoWork(){int count=0;
        Again:Thread.Sleep(5);if(retry){if(count>=2)throw new Exception();
        count++;Thread.Sleep(3);goto Again;}return 0;}}""")
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (5, 21)
    assert result["execution_status"] == "complete" and result["total_ms"] is None


def test_force_record_style_guard_allows_four_successful_attempts_before_failure():
    result = analyze("""class Demo {bool retry;public int DoWork(){int count=0;
        Record:for(int i=-180;i<=180;i+=5){Thread.Sleep(500);}
        if(retry){if(count>2)throw new Exception();Thread.Sleep(500);count++;goto Record;}
        return 0;}}""")
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (36500, 147500)


def test_unknown_unbounded_retry_stays_unknown_instead_of_becoming_one_iteration():
    result = analyze("""class Demo {bool retry;public int DoWork(){
        Again:Thread.Sleep(5);if(retry)goto Again;return 0;}}""")
    assert result["known_delay_min_ms"] == 5 and result["known_delay_max_ms"] is None
    assert result["total_ms"] is None


def test_jump_out_of_a_block_restores_a_same_named_member():
    result = analyze("""class Demo {int delay=5;public int DoWork(){
        {int delay=7;Thread.Sleep(delay);goto End;}End:Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 12


def test_labels_in_an_uninvoked_callback_do_not_belong_to_the_outer_jump_scope():
    result = analyze("""class Demo {public int DoWork(){Action ignored=()=>{
        End:Thread.Sleep(999);};goto End;Thread.Sleep(999);End:Thread.Sleep(7);return 0;}}""")
    assert result["total_ms"] == 7


@pytest.mark.parametrize(
    "loop",
    [
        "while(repeat){Thread.Sleep(3);goto End;}",
        "foreach(var x in values){Thread.Sleep(3);goto End;}",
    ],
)
def test_unknown_loop_transfers_to_an_outer_label_or_executes_its_normal_tail(loop):
    result = analyze(
        f"class Demo {{bool repeat;int[] values;public int DoWork(){{{loop}"
        "Thread.Sleep(10);End:Thread.Sleep(7);return 0;}}"
    )
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (10, 17)


def test_repeated_unknown_loop_before_a_jump_keeps_both_the_short_and_unbounded_paths():
    result = analyze("""class Demo {bool repeat,leave;public int DoWork(){
        while(repeat){if(leave)goto End;Thread.Sleep(3);}
        Thread.Sleep(10);End:Thread.Sleep(7);return 0;}}""")
    assert result["known_delay_min_ms"] == 7 and result["known_delay_max_ms"] is None


def test_unknown_loop_includes_repeated_cost_of_the_condition_itself():
    result = analyze("""class Demo {bool repeat;bool Next(){Thread.Sleep(2);return repeat;}
        public int DoWork(){while(Next()){}return 0;}}""")
    assert result["known_delay_min_ms"] == 2 and result["known_delay_max_ms"] is None


def test_finally_updates_state_before_resuming_the_jump():
    result = analyze("""class Demo {public int DoWork(){int delay=1;
        try{goto End;}finally{delay=7;Thread.Sleep(2);}
        Thread.Sleep(999);End:Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 9


def test_finally_uses_each_jump_branch_state():
    result = analyze("""class Demo {bool option;public int DoWork(){int delay=1;
        try{if(option){delay=3;goto EndA;}delay=5;goto EndB;}
        finally{delay+=2;Thread.Sleep(delay);}
        EndA:Thread.Sleep(delay);return 0;EndB:Thread.Sleep(delay);return 0;}}""")
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (10, 14)


def test_merged_jump_states_do_not_invent_a_known_delay_for_finally():
    result = analyze("""class Demo {bool option;public int DoWork(){int delay=1;
        try{if(option){delay=3;goto End;}delay=5;goto End;}
        finally{Thread.Sleep(delay);}End:Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None and result["known_delay_max_ms"] is None


def test_throwing_finally_prevents_the_jump_from_reaching_its_target():
    result = analyze("""class Demo {public int DoWork(){try{goto End;}
        finally{throw new Exception();}End:Thread.Sleep(999);return 0;}}""")
    assert result["execution_status"] == "unavailable"
    assert not any(s.get("milliseconds") == 999 for s in result["stages"])


def test_catch_jump_keeps_the_recovery_cost_unknown():
    result = analyze("""class Demo {public int DoWork(){try{throw new Exception();}
        catch{Thread.Sleep(3);goto End;}Thread.Sleep(999);End:Thread.Sleep(7);return 0;}}""")
    assert result["known_delay_min_ms"] == 10 and result["known_delay_max_ms"] is None
    assert not any(s.get("milliseconds") == 999 for s in result["stages"])


def test_closed_label_cycle_does_not_invent_a_successful_exit():
    result = analyze("""class Demo {public int DoWork(){
        Again:Thread.Sleep(5);goto Again;Thread.Sleep(999);return 0;}}""")
    assert result["execution_status"] == "unavailable" and result["total_ms"] is None
    assert result["known_delay_min_ms"] is None
    assert not any(s.get("milliseconds") == 999 for s in result["stages"])


def test_finally_waits_for_only_the_remaining_background_task_time():
    result = analyze("""class Demo {public int DoWork(){
        Task task=Task.Run(()=>Thread.Sleep(20));
        try{Thread.Sleep(5);goto End;}finally{task.Wait();}
        End:Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] == 23


@pytest.mark.parametrize(
    "loop",
    [
        "for(int delay=7;delay<8;delay++){Thread.Sleep(delay);goto End;}",
        "foreach(var delay in new[]{7}){Thread.Sleep(delay);goto End;}",
        "foreach(var delay in new[]{7}){Thread.Sleep(delay);break;}",
    ],
)
def test_loop_exit_restores_the_member_shadowed_by_its_iteration_variable(loop):
    result = analyze(
        f"class Demo {{int delay=5;public int DoWork(){{{loop}End:Thread.Sleep(delay);return 0;}}}}"
    )
    assert result["total_ms"] == 12


def test_repeated_unknown_retry_keeps_the_budget_for_mandatory_later_calls():
    result = analyze("""class Demo {bool retry;void Empty(){}
        void Work(){Empty();Empty();Empty();Empty();Empty();Empty();Thread.Sleep(2);}
        void Reset(){Again:Work();if(retry)goto Again;}
        void After(){Thread.Sleep(7);}
        public int DoWork(){Reset();After();return 0;}}""")
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (9, None)
    assert not any(s["label"] == "调用链达到展开边界" for s in result["stages"])


def test_retry_state_comparison_keeps_counters_written_by_a_called_method():
    result = analyze("""class Demo {int count=0;void Step(){count++;}
        public int DoWork(){Again:Thread.Sleep(2);Step();if(count<3)goto Again;
        Thread.Sleep(7);return 0;}}""")
    assert result["total_ms"] == 13
