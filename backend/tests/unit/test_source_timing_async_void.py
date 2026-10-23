"""async void只把同步前段返回调用者；Task等待不能接管其续体。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("methods", "body", "expected"),
    [
        (
            "async void Start(){Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);}",
            "Start();Thread.Sleep(7);",
            10,
        ),
        (
            "async void Start(){Thread.Sleep(3);await Task.Delay(0);Thread.Sleep(2);}",
            "Start();Thread.Sleep(7);",
            12,
        ),
        (
            "async void Start(){try{Thread.Sleep(3);await Task.Delay(20);}"
            "finally{Thread.Sleep(2);}}",
            "Start();Thread.Sleep(7);",
            10,
        ),
        (
            "async void Start(){Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);}",
            "Action cb=Start;cb();Thread.Sleep(7);",
            10,
        ),
        (
            "",
            "Action cb=async()=>{Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);};"
            "cb();Thread.Sleep(7);",
            10,
        ),
        (
            "",
            "Action cb=async()=>{Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);};"
            "Task.Run(cb).Wait();Thread.Sleep(7);",
            10,
        ),
        (
            "",
            "var t=new Task(async()=>{Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);});"
            "t.Start();t.Wait();Thread.Sleep(7);",
            10,
        ),
        (
            "",
            "var t=new Task(async()=>{Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);});"
            "t.RunSynchronously();Thread.Sleep(7);",
            10,
        ),
        (
            "async void Start(){Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);}",
            "Task.Run(Start).Wait();Thread.Sleep(7);",
            10,
        ),
        (
            "",
            "Task.Factory.StartNew(async()=>{Thread.Sleep(3);await Task.Delay(20);"
            "Thread.Sleep(2);}).Wait();Thread.Sleep(7);",
            10,
        ),
    ],
)
def test_only_the_synchronous_prefix_blocks_the_caller(methods, body, expected):
    result = analyze(f"class Demo {{{methods}public int DoWork(){{{body}return 0;}}}}")
    assert result["total_ms"] == expected
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected
    if "Task.Delay(20)" in methods + body:
        assert any(
            stage.get("milliseconds") == 20 and stage["background"] for stage in result["stages"]
        )


def test_async_void_body_as_an_action_entry_includes_its_own_continuation():
    result = analyze("""class Demo {public async void DoWork(){
        Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);}}""")
    assert result["total_ms"] == 25


def test_future_writes_from_async_void_do_not_replace_the_callers_current_value():
    result = analyze("""class Demo {int delay=5;async void Start(){await Task.Delay(20);delay=999;}
        public int DoWork(){Start();Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert not any(
        stage.get("milliseconds") == 999 and not stage["background"] for stage in result["stages"]
    )


def test_async_void_synchronous_writes_are_visible_before_the_first_pending_await():
    result = analyze("""class Demo {int delay=5;async void Start(){delay=7;await Task.Delay(20);}
        public int DoWork(){Start();Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 7
