"""顺序集合回调的次数、共享状态和未知硬件数量直接影响动作耗时。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


def listing(body, members=""):
    return analyze(
        "using System;using System.Collections.Generic;using System.Threading.Tasks;"
        "class Demo {" + members + "public int DoWork(){" + body + "return 0;}}"
    )


@pytest.mark.parametrize(
    "body,expected",
    [
        ("new List<int>{3,7,11}.ForEach(n=>Thread.Sleep(n));", 21),
        ("new List<int>().ForEach(n=>Thread.Sleep(999));Thread.Sleep(2);", 2),
        (
            "int delay=1;new List<int>{1,2,3}.ForEach(n=>{Thread.Sleep(delay);delay+=2;});"
            "Thread.Sleep(delay);",
            16,
        ),
        ("new List<int>{1,2}.ForEach(n=>{if(n==1)return;Thread.Sleep(7);});Thread.Sleep(3);", 10),
        ("var a=new List<int>{2,3};a.ForEach(n=>{a=new List<int>{99};Thread.Sleep(n);});", 5),
        ("new List<int>{2,3}.ForEach(Step);", 5),
        ("Action<int> cb=Step;new List<int>{2,3}.ForEach(cb);", 5),
        ("new List<int>{2,3}.ForEach(action:Step);", 5),
        ("new List<int>{2,3}.ForEach(n=>new List<int>{5,7}.ForEach(m=>Thread.Sleep(n+m)));", 34),
    ],
)
def test_list_callbacks_run_sequentially_and_callback_return_does_not_exit_the_action(
    body, expected
):
    result = listing(body, "void Step(int n){Thread.Sleep(n);}")
    assert result["total_ms"] == expected


def test_list_callback_captures_the_method_group_receiver_once():
    result = analyze("""using System;using System.Collections.Generic;
        class Target {public int delay;public void Step(int n){Thread.Sleep(delay);}}
        class Demo {public int DoWork(){var one=new Target{delay=3};
        var two=new Target{delay=7};var list=new List<int>{1,2};Action<int> cb=one.Step;
        list.ForEach(n=>{cb(n);one=two;});return 0;}}""")
    assert result["total_ms"] == 6


def test_unknown_hardware_count_preserves_the_per_light_wait_without_claiming_one_light():
    result = listing(
        "List<Light> lights=HardwareRepository.GetLights();"
        "lights.ForEach(a=>{a.SetIntensity(200);Thread.Sleep(2000);a.SetIntensity(0);});",
        "class Light {public void SetIntensity(int value){}}",
    )
    assert result["known_delay_min_ms"] == 0
    assert result["known_delay_max_ms"] is None
    assert result["total_ms"] is None
    loop = next(s for s in result["stages"] if s["kind"] == "loop")
    assert loop["iterations"] is None
    assert loop["per_iteration_min_ms"] == loop["per_iteration_max_ms"] == 2000
    assert loop["element_type"] == "Light"
    assert result["per_item_timing"] == [{"element_type": "Light", "min_ms": 2000, "max_ms": 2000}]
    assert any(
        s["kind"] == "delay" and s["milliseconds"] == 2000 and s["repeat"] for s in result["stages"]
    )


def test_unknown_count_cannot_leave_the_state_of_one_sample_callback_as_the_final_state():
    result = listing(
        "int delay=3;List<int> list=ReadList();list.ForEach(n=>delay=7);Thread.Sleep(delay);"
    )
    assert result["total_ms"] is None
    assert result["known_delay_min_ms"] == 0


@pytest.mark.parametrize("mutation", ["list.Add(5);", "list.Clear();", "list[0]=9;"])
def test_modifying_the_enumerated_list_does_not_produce_a_successful_fixed_total(mutation):
    result = listing(
        "var list=new List<int>{2};list.ForEach(n=>{Thread.Sleep(n);" + mutation + "});"
    )
    assert result["total_ms"] is None
    assert any(s["kind"] == "unresolved" and "修改" in s["label"] for s in result["stages"])


def test_mutating_another_list_does_not_invalidate_the_receiver():
    result = listing(
        "var one=new List<int>{2,3};var two=new List<int>();"
        "one.ForEach(n=>{two.Add(n);Thread.Sleep(n);});"
    )
    assert result["total_ms"] == 5


def test_a_known_throwing_handler_does_not_execute_the_next_item():
    result = listing(
        "new List<int>{1,2}.ForEach(n=>{if(n==1)throw new Exception();Thread.Sleep(999);});"
    )
    assert result["total_ms"] is None
    assert not any(s["kind"] == "delay" and s["milliseconds"] == 999 for s in result["stages"])


def test_async_void_callback_is_not_joined_by_list_foreach():
    result = listing(
        "new List<int>{1,2}.ForEach(async n=>{Thread.Sleep(n);await Task.Delay(100);"
        "Thread.Sleep(7);});Thread.Sleep(3);"
    )
    assert result["total_ms"] == 6
    assert any(
        s["kind"] == "delay" and s["milliseconds"] == 100 and s["background"]
        for s in result["stages"]
    )


def test_source_owned_foreach_is_executed_as_source_and_not_as_framework_list():
    result = analyze("""using System;class List<T>{
        public void ForEach(Action<T> action){Thread.Sleep(17);}}
        class Demo {public int DoWork(){new List<int>().ForEach(n=>Thread.Sleep(999));
        return 0;}}""")
    assert result["total_ms"] == 17


def test_unknown_callback_is_reported_even_for_an_empty_list_because_null_is_invalid():
    result = listing("Action<int> cb=ReadCallback();new List<int>().ForEach(cb);")
    assert result["total_ms"] is None


def test_expansion_budget_retains_a_known_prefix_and_unknown_remainder():
    result = listing(
        "var list=new List<int>();for(int n=0;n<129;n++)list.Add(1);"
        "list.ForEach(n=>Thread.Sleep(n));"
    )
    assert result["total_ms"] is None
    assert result["truncated"]


def test_unknown_collection_with_a_noop_callback_still_has_an_unknown_iteration_boundary():
    result = listing("List<int> list=ReadList();list.ForEach(n=>{});")
    assert result["total_ms"] is None
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 0


def test_list_budget_keeps_the_executed_prefix_and_does_not_count_the_tail_sample(monkeypatch):
    from app.modules.action_timing import source_list_callbacks

    monkeypatch.setattr(source_list_callbacks, "MAX_ITERATIONS", 2)
    result = listing("new List<int>{1,2,3}.ForEach(n=>Thread.Sleep(n));")
    assert result["known_delay_min_ms"] == 3
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
    assert result["truncated"]
    loop = next(stage for stage in result["stages"] if stage["kind"] == "loop")
    assert loop["expanded_iterations"] == 2 and loop["iterations"] is None


def test_reassigning_the_callback_variable_does_not_replace_the_list_invocation_snapshot():
    result = listing("""Action<int> callback=null;
        callback=n=>{Thread.Sleep(n);callback=k=>Thread.Sleep(999);};
        new List<int>{2,3}.ForEach(callback);""")
    assert result["total_ms"] == 5


def test_unknown_count_keeps_the_preceding_wait_and_each_item_as_separate_quantities():
    result = listing(
        "List<int> items=ReadList();Thread.Sleep(11);items.ForEach(n=>Thread.Sleep(7));"
    )
    assert result["known_delay_min_ms"] == 11
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
    assert result["per_item_timing"] == [{"element_type": "int", "min_ms": 7, "max_ms": 7}]
