"""回调执行于调用位置；捕获变量与被调方法的同名局部变量必须隔离。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("declarations", "body", "expected"),
    [
        (
            "void Run(Action cb) {Thread.Sleep(2); cb?.Invoke(); Thread.Sleep(3);}",
            "Run(()=>Thread.Sleep(7));",
            12,
        ),
        ("", "Action cb=()=>Thread.Sleep(7); cb(); cb.Invoke();", 14),
        (
            "void Run(Action cb) {Forward(cb);} void Forward(Action next) {next();}",
            "Run(()=>Thread.Sleep(11));",
            11,
        ),
        (
            "void Run(Action cb) {int delay=999; cb();}",
            "int delay=5; Run(()=>Thread.Sleep(delay));",
            5,
        ),
        (
            "void Run(Action cb) {cb();}",
            "int delay=5; Run(()=>{delay=7;}); Thread.Sleep(delay);",
            7,
        ),
        (
            "void Run(Action cb) {cb();}",
            "int delay=5; Action cb=()=>Thread.Sleep(delay); delay=9; Run(cb);",
            9,
        ),
        (
            "int delay=13; void Work(){Thread.Sleep(delay);} void Run(Action cb){cb();}",
            "Run(Work);",
            13,
        ),
        ("void Run(Action cb=null) {cb?.Invoke(); Thread.Sleep(3);}", "Run();", 3),
        ("void Run(Action cb) {cb?.Invoke(); Thread.Sleep(3);}", "Run(null);", 3),
        ("void Run(Action<int> cb){cb(7);}", "Run(n=>Thread.Sleep(n));", 7),
        ("void Run(Action<int> cb){cb.Invoke(7);}", "Run((int n)=>Thread.Sleep(n));", 7),
        ("", "Func<Task> cb=()=>Task.Delay(17); await cb();", 17),
        ("", "await Task.Run(async ()=>{await Task.Delay(19);});", 19),
        (
            "void Run(Action cb){cb();}",
            "int delay=5; await Task.Run(()=>Run(()=>{delay=7;})); Thread.Sleep(delay);",
            7,
        ),
    ],
)
def test_bound_callback_timing_and_closure_state(declarations, body, expected):
    result = analyze(f"class Demo {{ {declarations} public int DoWork() {{{body} return 0;}} }}")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected
    assert result["total_ms"] == expected


def test_callback_uses_creating_instance_instead_of_helper_this():
    result = analyze("""class Helper {int delay=999; public void Run(Action cb){cb();}}
        class Demo {int delay=13; public int DoWork(){
            new Helper().Run(()=>Thread.Sleep(delay)); return 0;}}""")
    assert result["total_ms"] == 13


@pytest.mark.parametrize(
    "body",
    [
        "Action cb=ExternalCallback(); cb();",
        "int delay=5; Task.Run(()=>Run(()=>{delay=7;})); Thread.Sleep(delay);",
        "int delay=5; Action cb=()=>Thread.Sleep(delay); if(flag) delay=9; cb();",
        "Action cb=null; cb();",
        "Action cb=async ()=>{await Task.Delay(20);}; cb();",
        "Action cb=async ()=>{await Task.Delay(20);}; Task.Run(cb).Wait();",
    ],
)
def test_unknown_callback_order_or_target_does_not_become_a_known_total(body):
    result = analyze(
        f"class Demo {{void Run(Action cb){{cb();}} public int DoWork(){{{body} return 0;}}}}"
    )
    assert result["total_ms"] is None


@pytest.mark.parametrize("kind", ["Func<Task>", "System.Func<Task>"])
def test_unjoined_task_callback_returns_after_starting_the_delay(kind):
    result = analyze(f"""class Demo {{public int DoWork(){{
        {kind} cb=()=>Task.Delay(20);cb();return 0;}}}}""")
    assert result["total_ms"] == 0
    assert any(
        stage["background"] and stage.get("milliseconds") == 20 for stage in result["stages"]
    )


def test_same_named_invoke_on_source_object_is_not_a_delegate():
    result = analyze("""class Worker {public void Invoke(){Thread.Sleep(17);}}
        class Demo {public int DoWork(){new Worker().Invoke();return 0;}}""")
    assert result["total_ms"] == 17


def test_null_conditional_callback_does_not_evaluate_its_arguments():
    result = analyze("""class Demo {public int DoWork(){Action<int> cb=null;
        cb?.Invoke(Read());Thread.Sleep(3);return 0;}
        int Read(){Thread.Sleep(999);return 7;}}""")
    assert result["total_ms"] == 3


def test_callback_local_variables_are_new_on_each_invocation():
    result = analyze("""class Demo {public int DoWork(){
        Action cb=()=>{int delay=5;Thread.Sleep(delay);delay=9;};
        cb();cb();return 0;}}""")
    assert result["total_ms"] == 10


def test_async_void_method_group_does_not_appear_to_finish_its_awaited_body():
    result = analyze("""class Demo {public int DoWork(){
        Task.Run(Work).Wait(); return 0;}
        async void Work(){await Task.Delay(20);}}""")
    assert result["total_ms"] is None
    assert all(stage["background"] for stage in result["stages"] if stage["kind"] == "delay")
