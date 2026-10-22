"""while前测、do后测；退出状态和回调条件按实际执行时点保留。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("int i=0;while(i<3){Thread.Sleep(2);i++;}Thread.Sleep(i);", 9),
        ("int i=0;do{Thread.Sleep(2);i++;}while(i<3);Thread.Sleep(i);", 9),
        ("int delay=1;while(true){delay=7;break;}Thread.Sleep(delay);", 7),
        ("int delay=1;do{delay=7;break;}while(false);Thread.Sleep(delay);", 7),
        ("int i=0;while(i<5){i++;if(i==2)continue;Thread.Sleep(3);}", 12),
        ("int i=0;do{i++;if(i==2)continue;Thread.Sleep(3);}while(i<5);", 12),
        ("int i=0;while(i<5){if(i==2)return 0;Thread.Sleep(3);i++;}Thread.Sleep(999);", 6),
        ("int i=0;do{Thread.Sleep(3);i++;if(i==2)break;}while(i<5);Thread.Sleep(7);", 13),
    ],
)
def test_condition_loop_iteration_timing_and_exit_state(body, expected):
    result = analyze(f"class Demo {{public int DoWork(){{{body}return 0;}}}}")
    assert result["total_ms"] == expected


@pytest.mark.parametrize(("keyword", "expected"), [("while", 17), ("do", 15)])
def test_side_effecting_condition_is_executed_before_or_after_the_body(keyword, expected):
    loop = (
        "while(Next()){Thread.Sleep(3);counter++;}"
        if keyword == "while"
        else ("do{Thread.Sleep(3);counter++;}while(Next());")
    )
    result = analyze(
        "class Demo {int counter;bool Next(){Thread.Sleep(2);return counter<3;}"
        f"public int DoWork(){{counter=0;{loop}return 0;}}}}"
    )
    assert result["total_ms"] == expected


def test_do_break_does_not_evaluate_the_condition_or_its_side_effects():
    result = analyze("""class Demo {int delay=5;
        bool Next(){delay=999;Thread.Sleep(100);return false;}
        public int DoWork(){do{Thread.Sleep(3);break;}while(Next());
        Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 8
    assert not any(stage.get("milliseconds") in {100, 999} for stage in result["stages"])


def test_do_condition_observes_the_state_written_by_the_first_body():
    result = analyze("""class Demo {bool ready;
        bool Next(){Thread.Sleep(2);return ready;}
        public int DoWork(){ready=true;do{Thread.Sleep(3);ready=false;}while(Next());return 0;}}""")
    assert result["total_ms"] == 5


def test_unknown_signal_condition_keeps_one_mandatory_do_delay_and_unbounded_wait():
    result = analyze("""class Demo {External signal;
        public int DoWork(){do{Thread.Sleep(5);}while(!signal.WaitOne(100));return 0;}}""")
    assert result["known_delay_min_ms"] == 5
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
    assert next(s for s in result["stages"] if s["kind"] in {"delay", "wait"})["kind"] == "delay"


def test_loop_condition_uses_this_invocations_actual_property_result():
    result = analyze("""class Demo {int counter;
        bool Next {get{Thread.Sleep(2);return counter<3;}}
        public int DoWork(){counter=0;while(Next){Thread.Sleep(3);counter++;}return 0;}}""")
    assert result["total_ms"] == 17


def test_loop_condition_uses_bound_func_return_value():
    result = analyze("""class Demo {public int DoWork(){int i=0;
        Func<bool> next=()=>{Thread.Sleep(2);return i<3;};
        while(next()){Thread.Sleep(3);i++;}return 0;}}""")
    assert result["total_ms"] == 17


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("int i=0;while(i++<3){Thread.Sleep(2);}Thread.Sleep(i);", 10),
        ("int i=0;while(++i<3){Thread.Sleep(2);}Thread.Sleep(i);", 7),
        ("int i=0;while((i+=2)<=6){Thread.Sleep(i);}", 12),
    ],
)
def test_prefix_postfix_and_assignment_conditions_return_their_evaluated_values(body, expected):
    result = analyze(f"class Demo {{public int DoWork(){{{body}return 0;}}}}")
    assert result["total_ms"] == expected


def test_property_getter_can_return_the_value_before_its_postincrement():
    result = analyze("""class Demo {int count;int Next {get{return count++;}}
        public int DoWork(){count=0;while(Next<3){Thread.Sleep(2);}return 0;}}""")
    assert result["total_ms"] == 6


def test_func_method_group_can_supply_the_actual_condition_result():
    result = analyze("""class Demo {int count;bool Next(){return count++<3;}
        public int DoWork(){count=0;Func<bool> next=Next;
        while(next()){Thread.Sleep(2);}return 0;}}""")
    assert result["total_ms"] == 6


def test_body_integer_overflow_does_not_prove_a_finite_while_exit():
    result = analyze("""class Demo {public int DoWork(){int i=2147483646;
        while(i<=2147483647){Thread.Sleep(2);i++;}return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


@pytest.mark.parametrize("loop", ["while(true)", "for(;;)"])
def test_literal_true_loop_without_an_exit_has_no_normal_action_duration(loop):
    result = analyze(
        f"class Demo {{public int DoWork(){{{loop}{{Thread.Sleep(5);}}"
        "Thread.Sleep(999);return 0;}}"
    )
    assert result["execution_status"] == "unavailable"
    assert result["known_delay_min_ms"] is None and result["total_ms"] is None
    assert not any(s.get("milliseconds") == 999 for s in result["stages"])


def test_forever_background_worker_does_not_make_the_start_method_unavailable():
    result = analyze("""class Demo {public int DoWork(){
        Task.Run(()=>{while(true){Thread.Sleep(5);}});Thread.Sleep(7);return 0;}}""")
    assert result["total_ms"] == 7 and result["execution_status"] == "complete"


@pytest.mark.parametrize(
    ("expression", "answer", "expected"),
    [("++i<3 && Next()", "true", 13), ("++i<3 || Next()", "false", 11)],
)
def test_short_circuit_condition_uses_the_evaluated_left_value(expression, answer, expected):
    result = analyze(
        f"class Demo {{bool Next(){{Thread.Sleep(2);return {answer};}}"
        "public int DoWork(){int i=0;"
        f"while({expression}){{Thread.Sleep(3);}}Thread.Sleep(i);return 0;}}}}"
    )
    # &&只调用两次Next，||只在第三次左条件变false时调用一次。
    assert result["total_ms"] == expected


def test_arrow_func_return_uses_the_actual_postincrement_result():
    result = analyze("""class Demo {int i;bool Next()=>i++<3;
        public int DoWork(){i=0;Func<bool> next=Next;
        while(next()){Thread.Sleep(2);}return 0;}}""")
    assert result["total_ms"] == 6


def test_unchanged_unknown_exit_loop_keeps_a_compact_repeat_instead_of_128_samples():
    result = analyze("""class Demo {bool stop;public int DoWork(){
        while(true){if(stop)break;Thread.Sleep(2);}return 0;}}""")
    delays = [s for s in result["stages"] if s["kind"] == "delay"]
    assert result["known_delay_min_ms"] == 0 and result["known_delay_max_ms"] is None
    assert result["total_ms"] is None
    assert len(delays) <= 3 and any(s.get("repeat") for s in delays)


def test_signal_reset_initializer_is_not_the_live_state_of_a_running_poll():
    result = analyze("""using AKRS.Galaxy2.Machine.Models;
        class Demo {Signal signal;public int DoWork(){
        while(signal.State!=SignalStateEnum.Set){Thread.Sleep(10);}Thread.Sleep(7);return 0;}}
        namespace AKRS.Galaxy2.Machine.Models {enum SignalStateEnum{Set,ReSet}
        class Signal {public SignalStateEnum State {get;set;}=SignalStateEnum.ReSet;}}""")
    assert result["known_delay_min_ms"] == 7
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None


def test_unknown_coordinate_parent_chain_does_not_expand_an_arbitrary_128_links():
    result = analyze("""using System.Collections.Generic;
        class Frame {public Frame Parent {get;set;}}
        class Demo {Frame frame;public int DoWork(){var item=frame;var frames=new List<Frame>();
        while(true){if(item.Parent!=null){frames.Add(item);item=item.Parent;}else break;}
        Thread.Sleep(7);return 0;}}""")
    loop = next(s for s in result["stages"] if s["kind"] == "loop")
    assert loop["expanded_iterations"] <= 2
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (7, 7)
    assert result["total_ms"] is None


@pytest.mark.parametrize("last", ["return;", "Thread.Sleep(3);"])
def test_expansion_limit_keeps_cpu_unknown_separate_from_possible_fixed_delays(last):
    methods = "".join(f"void M{i}(){{M{i + 1}();}}" for i in range(9))
    result = analyze(
        f"class Demo {{{methods}void M9(){{{last}}}"
        "public int DoWork(){M0();Thread.Sleep(7);return 0;}}"
    )
    assert result["known_delay_min_ms"] == 7 and result["total_ms"] is None
    assert result["known_delay_max_ms"] == (7 if last == "return;" else None)
