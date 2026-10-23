"""反射委托按实际签名展开；返回任务、参数数组与同步调用边界分别核对。"""

import json

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("declarations", "body", "expected"),
    [
        ("", "Action cb=()=>Thread.Sleep(7);cb.DynamicInvoke();", 7),
        ("", "Delegate cb=(Action<int>)(n=>Thread.Sleep(n));cb.DynamicInvoke(7);", 7),
        (
            "",
            "Delegate cb=(Action<int>)(n=>Thread.Sleep(n));cb.DynamicInvoke(new object[]{11});",
            11,
        ),
        ("", "Action cb=()=>Thread.Sleep(7);cb.DynamicInvoke(null);", 7),
        ("", "Action<int> cb=n=>Thread.Sleep(n);cb?.DynamicInvoke(7);", 7),
        (
            "void Work(int n){Thread.Sleep(n);}",
            "Delegate cb=new Action<int>(Work);cb.DynamicInvoke(7);",
            7,
        ),
        (
            "void Run(Delegate cb){if(cb==null)return;cb.DynamicInvoke();}",
            "Run((Action)(()=>Thread.Sleep(7)));",
            7,
        ),
        ("", "Action cb=()=>Thread.Sleep(7);cb.DynamicInvoke(args:new object[0]);", 7),
        (
            "",
            "Func<int> cb=()=>{Thread.Sleep(2);return 13;};Thread.Sleep((int)cb.DynamicInvoke());",
            15,
        ),
        (
            "void Run(Delegate cb,object[] args){cb.DynamicInvoke(args);}",
            "Action<int> cb=n=>Thread.Sleep(n);Run(cb,new object[]{17});",
            17,
        ),
        (
            "void Run(Delegate cb,object[] args){Task.Run(()=>cb.DynamicInvoke(args)).Wait();}",
            "Action<int> cb=n=>Thread.Sleep(n);Run(cb,new object[]{19});",
            19,
        ),
        (
            "void Run(Delegate cb){if(cb is Func<Task> asyncFunc){"
            "((Task)asyncFunc.DynamicInvoke()).Wait();}"
            "else{cb.DynamicInvoke();}}",
            "Func<Task> cb=()=>Task.Delay(23);Run(cb);",
            23,
        ),
        (
            "void Run(Delegate cb){if(cb is Func<Task> asyncFunc){"
            "((Task)asyncFunc.DynamicInvoke()).Wait();}"
            "else{cb.DynamicInvoke();}}",
            "Action cb=()=>Thread.Sleep(29);Run(cb);",
            29,
        ),
        (
            "",
            "int delay=5;Delegate cb=(Action)(()=>delay=7);cb.DynamicInvoke();Thread.Sleep(delay);",
            7,
        ),
    ],
)
def test_known_dynamic_delegate_follows_its_values_and_target(declarations, body, expected):
    result = analyze(f"class Demo {{{declarations} public int DoWork(){{{body} return 0;}}}}")
    assert result["total_ms"] == expected
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected
    json.dumps(result)


def test_dynamic_task_return_is_started_before_it_is_joined():
    result = analyze("""class Demo {public int DoWork(){
        Delegate cb=(Func<Task>)(async()=>{Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);});
        Task t=(Task)cb.DynamicInvoke();Thread.Sleep(5);t.Wait();Thread.Sleep(7);return 0;}}""")
    assert result["total_ms"] == 32
    assert all(not row["background"] for row in result["stages"] if row["kind"] == "delay")


def test_dynamic_async_action_only_waits_for_the_synchronous_prefix():
    result = analyze("""class Demo {public int DoWork(){
        Delegate cb=(Action)(async()=>{Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);});
        cb.DynamicInvoke();Thread.Sleep(7);return 0;}}""")
    assert result["total_ms"] == 10
    assert any(row["background"] and row.get("milliseconds") == 20 for row in result["stages"])


def test_dynamic_receiver_is_saved_before_argument_evaluation_changes_it():
    result = analyze("""class Demo {Delegate cb;
        int Change(){cb=(Action<int>)(n=>Thread.Sleep(999));return 7;}
        public int DoWork(){cb=(Action<int>)(n=>Thread.Sleep(n));
        cb.DynamicInvoke(Change());return 0;}}""")
    assert result["total_ms"] == 7


def test_same_named_source_member_still_uses_its_actual_body():
    result = analyze("""class Worker {public void DynamicInvoke(){Thread.Sleep(17);}}
        class Demo {public int DoWork(){new Worker().DynamicInvoke();return 0;}}""")
    assert result["total_ms"] == 17


@pytest.mark.parametrize(
    "body",
    [
        "Delegate cb=External();cb.DynamicInvoke();",
        "Action<int> cb=n=>Thread.Sleep(n);cb.DynamicInvoke(Unknown());",
        "Action<int> cb=n=>Thread.Sleep(n);cb.DynamicInvoke(new object[]{7,11});",
        "Action<int> cb=n=>Thread.Sleep(n);cb.DynamicInvoke(new object[]{true});",
        "Action<int> cb=n=>Thread.Sleep(n);cb.DynamicInvoke(new object[]{7L});",
        "Action<int> cb=n=>Thread.Sleep(n);object[] args=new object[]{7};"
        "args[0]=7L;cb.DynamicInvoke(args);",
        "Action<int> cb=n=>Thread.Sleep(n);cb.DynamicInvoke(new object[]{null});",
        "Action<int> cb=n=>Thread.Sleep(n);cb.DynamicInvoke(UnknownArray());",
        "Action cb=null;cb.DynamicInvoke();",
    ],
)
def test_unknown_or_invalid_dynamic_binding_cannot_supply_a_fixed_total(body):
    result = analyze(f"class Demo {{public int DoWork(){{{body}return 0;}}}}")
    assert result["total_ms"] is None


def test_null_conditional_dynamic_delegate_skips_argument_side_effects():
    result = analyze("""class Demo {int Read(){Thread.Sleep(999);return 7;}
        public int DoWork(){Action<int> cb=null;cb?.DynamicInvoke(Read());
        Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] == 3


@pytest.mark.parametrize("launch", ["Task t=Work();t.Wait();", "Work().GetAwaiter().GetResult();"])
def test_first_incomplete_await_is_one_stage_owned_by_the_joined_task(launch):
    result = analyze(f"""class Demo {{async Task Work(){{Thread.Sleep(3);await Task.Delay(20);}}
        public int DoWork(){{{launch}return 0;}}}}""")
    assert result["total_ms"] == 23
    delays = [row for row in result["stages"] if row["kind"] == "delay"]
    assert [row["milliseconds"] for row in delays] == [3, 20]
    assert all(not row["background"] for row in delays)


def test_joining_async_method_keeps_its_unjoined_child_in_the_background():
    result = analyze("""class Demo {async Task Work(){Task.Run(()=>Thread.Sleep(999));
        await Task.Delay(20);}public int DoWork(){Work().Wait();return 0;}}""")
    assert result["total_ms"] == 20
    delays = [row for row in result["stages"] if row["kind"] == "delay"]
    assert len(delays) == 2
    assert next(row for row in delays if row["milliseconds"] == 999)["background"]
    assert not next(row for row in delays if row["milliseconds"] == 20)["background"]


def test_forwarding_an_old_task_through_dynamic_invoke_does_not_replay_its_write():
    result = analyze("""class Demo {int delay=5;public int DoWork(){
        Task old=Task.Run(()=>{Thread.Sleep(20);delay=9;});Thread.Sleep(30);delay=7;
        Func<Task> cb=()=>old;((Task)cb.DynamicInvoke()).Wait();Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 37


def test_closure_reassignment_invalidates_the_old_delegate_target():
    result = analyze("""class Demo {void Run(Action change){change();}public int DoWork(){
        Action cb=()=>Thread.Sleep(999);Run(()=>cb=()=>Thread.Sleep(7));
        cb.DynamicInvoke();return 0;}}""")
    assert result["total_ms"] == 7


def test_dynamic_delegate_keeps_its_bound_instance():
    result = analyze("""class Worker {int delay;public Worker(int n){delay=n;}
        public void Work(){Thread.Sleep(delay);}}
        class Demo {public int DoWork(){Worker worker=new Worker(11);
        Delegate cb=new Action(worker.Work);
        cb.DynamicInvoke();return 0;}}""")
    assert result["total_ms"] == 11


def test_value_type_array_is_one_boxed_argument_instead_of_an_object_argument_list():
    result = analyze("""struct Value {} class Demo {public int DoWork(){
        Action<Value> cb=n=>Thread.Sleep(7);Value[] values=new Value[1];
        cb.DynamicInvoke(values);return 0;}}""")
    assert result["total_ms"] is None


def test_future_delegate_reassignment_cannot_reuse_the_old_target():
    result = analyze("""class Demo {public int DoWork(){Action cb=()=>Thread.Sleep(999);
        Task.Run(()=>{cb=()=>Thread.Sleep(7);});cb.DynamicInvoke();return 0;}}""")
    assert result["total_ms"] is None


def test_explicit_null_ejection_task_does_not_create_a_timeout_failure_branch():
    result = analyze("""class Demo {public int DoWork(){Task ejectTask=null;
        if(false)ejectTask=Task.Run(()=>Thread.Sleep(999));
        if(ejectTask!=null){if(ejectTask.Wait(2000)==false)return 0;}
        Thread.Sleep(100);return 0;}}""")
    assert result["total_ms"] == 100
    assert result["timeout_count"] == 0
    assert [row["milliseconds"] for row in result["stages"] if row["kind"] == "delay"] == [100]


def test_explicit_null_hardware_reference_skips_its_conditional_output():
    result = analyze("""class Demo {public int DoWork(){Electric vacuum=null;
        vacuum?.SetOutputValue(false);Thread.Sleep(7);return 0;}}""")
    assert result["total_ms"] == 7
    assert not any(row["kind"] == "call" for row in result["stages"])
