"""业务实际使用的方法组、冷任务与任务数组，按启动和完成边界计算。"""

import pytest

from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.workspace import Workspace
from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("var t=new Task(() => { Thread.Sleep(20); }); Thread.Sleep(3);", 3),
        ("var t=new Task(() => { Thread.Sleep(20); }); Thread.Sleep(3); t.Start(); t.Wait();", 23),
        ("var t=new Task(() => { Thread.Sleep(20); }); t.Start(); Thread.Sleep(7); t.Wait();", 20),
        ("var t=new Task(() => { Thread.Sleep(20); }); t.RunSynchronously(); Thread.Sleep(3);", 23),
        ("var t=new Task(() => { Thread.Sleep(20); }); var other=t; other.Start(); t.Wait();", 20),
        (
            "int delay=5; var t=new Task(() => { Thread.Sleep(delay); });"
            "delay=9; t.Start(); t.Wait();",
            9,
        ),
        ("await Task.Run(() => Task.Delay(20));", 20),
        ("await Task.Run(() => { Thread.Sleep(5); return Task.Delay(20); });", 25),
        (
            "var a=Task.Delay(20); var b=Task.Delay(30);"
            "var group=new[] {a,b}; Task.WaitAll(group);",
            30,
        ),
        ("var a=Task.Delay(20); var b=a; Thread.Sleep(7); b.Wait();", 20),
        ("Task.WaitAll(new Task[] {}); Thread.Sleep(3);", 3),
        (
            "var t=new Task(() => Thread.Sleep(20)); var group=new[] {t};"
            "t.Start(); Task.WaitAll(group);",
            20,
        ),
    ],
)
def test_task_creation_start_and_join_timeline(body, expected):
    result = analyze(f"class Demo {{ public int DoWork() {{ {body} return 0; }} }}")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected
    assert result["total_ms"] == expected


@pytest.mark.parametrize(
    "body",
    [
        "var t=new Task(() => Thread.Sleep(20)); t.Wait();",
        "var t=Task.Delay(20); t=ExternalTask(); t.Wait();",
        "var a=Task.Delay(20); Task.WaitAll(new[] {a, missing});",
        "var a=Task.Delay(20); var group=new[] {a, missing}; Task.WaitAll(group);",
        "Task.WaitAny(new Task[] {});",
        "Task.Factory.StartNew(async () => { await Task.Delay(20); }).Wait();",
        "var t=new Task(async () => { await Task.Delay(20); }); t.Start(); t.Wait();",
        "Task.Delay(20).Wait(5);",
        "var t=Task.Delay(20); t.Wait(cancelToken);",
        "var a=Task.Delay(20); var group=new[] {a}; group[0]=missing; Task.WaitAll(group);",
        "Task.Run(() => Thread.Sleep(20), cancelToken).Wait();",
        "var a=Task.Delay(20); var b=Task.Delay(30); (a,b)=ExternalTasks(); a.Wait();",
    ],
)
def test_unstarted_reassigned_or_incomplete_task_cannot_become_known_completion(body):
    result = analyze(f"class Demo {{ public int DoWork() {{ {body} return 0; }} }}")
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


@pytest.mark.parametrize("expression", ["Work", "this.Work", "new Action(Work)", "(Action)(Work)"])
def test_task_method_group_is_bound_at_execution(expression):
    result = analyze(f"""class Demo {{ public int DoWork() {{
        Task.Run({expression}).Wait(); return 0; }}
        void Work() {{ Thread.Sleep(13); }} }}""")
    assert result["total_ms"] == 13
    assert any(
        stage["milliseconds"] == 13 for stage in result["stages"] if stage["kind"] == "delay"
    )


def test_deferred_delegate_does_not_write_before_start_and_uses_current_capture():
    result = analyze("""class Demo { static int delay=5; public int DoWork() {
        var t=new Task(() => { delay=9; Thread.Sleep(delay); });
        Thread.Sleep(delay); t.Start(); t.Wait(); return 0; } }""")
    assert result["total_ms"] == 14
    assert [stage["milliseconds"] for stage in result["stages"] if stage["kind"] == "delay"] == [
        5,
        9,
    ]


def test_method_group_captures_receiver_at_creation_while_lambda_captures_variable():
    source = """class Worker { public int delay; public void Work() { Thread.Sleep(delay); } }
        class Demo { public int DoWork() {
            var first=new Worker { delay=5 }; var second=new Worker { delay=9 };
            Worker selected=first; BODY return 0; } }"""
    group = analyze(
        source.replace(
            "BODY", "var t=new Task(selected.Work);selected=second; t.Start(); t.Wait();"
        )
    )
    assert group["total_ms"] == 5
    closure = analyze(
        source.replace(
            "BODY", "var t=new Task(() => selected.Work());selected=second; t.Start(); t.Wait();"
        )
    )
    assert closure["total_ms"] == 9


def test_method_group_virtual_dispatch_and_returned_task_remain_unresolved():
    virtual = analyze("""class Base { public virtual void Work() { Thread.Sleep(999); } }
        class Child : Base { public override void Work() { Thread.Sleep(13); } }
        class Demo { Base worker; public int DoWork() {
            Task.Run(worker.Work).Wait(); return 0; } }""")
    assert virtual["total_ms"] is None
    assert not any(stage.get("milliseconds") == 999 for stage in virtual["stages"])
    returned = analyze("""class Demo { public int DoWork() {
        Task.Run(Work).Wait(); return 0; }
        Task Work() { Thread.Sleep(5); return ExternalTask(); } }""")
    assert returned["total_ms"] is None


def test_same_named_source_task_uses_its_own_implementation():
    result = analyze("""class Task { public static void Delay(int ms) { Thread.Sleep(17); } }
        class Demo { public int DoWork() { Task.Delay(999); return 0; } }""")
    assert result["total_ms"] == 17
    local = analyze("""class Own { public void Run(int n) { Thread.Sleep(19); } }
        class Demo { public int DoWork() { Own Task=new Own(); Task.Run(999); return 0; } }""")
    assert local["total_ms"] == 19


def test_deconstruction_still_evaluates_source_call_once_without_a_single_variable_name():
    result = analyze("""class Demo { public int DoWork() {
        var (x,y)=Pair(); Thread.Sleep(3); return 0; }
        (int,int) Pair() { Thread.Sleep(7); return (1,2); } }""")
    assert result["total_ms"] == 10


def test_method_group_only_launcher_is_in_catalog_and_reports_background_source(tmp_path):
    source = tmp_path / "Main.cs"
    source.write_text(
        """class Demo { void ButtonClick() { Task.Run(Work); }
        void Work() { Thread.Sleep(13); } }""",
        encoding="utf-8",
    )
    report = SourceTiming(Workspace(tmp_path)).report()
    launcher = next(row for row in report["rows"] if row["method"] == "ButtonClick")
    assert launcher["total_ms"] == 0
    assert any(
        stage["kind"] == "delay" and stage["background"] and stage["milliseconds"] == 13
        for stage in launcher["stages"]
    )
