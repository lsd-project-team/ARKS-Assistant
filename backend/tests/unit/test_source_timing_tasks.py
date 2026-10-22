"""时间线反例：并行任务相加、已过去的延时重复计入、未等待任务误充同步时间。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("await Task.Delay(20); Thread.Sleep(3);", 23),
        ("Task.Delay(20); Thread.Sleep(3);", 3),
        ("Task.Delay(20).Wait(); Thread.Sleep(3);", 23),
        ("await Task.Run(() => { Thread.Sleep(20); }); Thread.Sleep(3);", 23),
        ("var t=Task.Run(() => { Thread.Sleep(20); }); Thread.Sleep(3); t.Wait();", 20),
        ("var t=Task.Delay(20); Thread.Sleep(30); t.Wait();", 30),
        ("var t=Task.Delay(20); await t.ConfigureAwait(false);", 20),
        ("var t=Task.Delay(20); await t;", 20),
        ("var t=Task.Delay(20); t.GetAwaiter().GetResult();", 20),
        ("var a=Task.Delay(20); var b=Task.Delay(30); Task.WaitAll(a,b);", 30),
        ("var a=Task.Delay(20); var b=Task.Delay(30); await Task.WhenAny(a,b);", 20),
        ("await Task.WhenAll(Task.Delay(20), Task.Delay(30));", 30),
    ],
)
def test_task_wait_boundaries(body, expected):
    result = analyze(f"class Demo {{ public int DoWork() {{ {body} return 0; }} }}")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected
    assert result["total_ms"] == expected


def test_unknown_task_io_or_dynamic_array_does_not_become_known_zero():
    result = analyze("""class Demo { public int DoWork() {
        var t=Task.Run(() => { axis.AbsoluteMove(target); }); t.Wait(); return 0; } }""")
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
    dynamic = analyze("class Demo { public int DoWork() { Task.WaitAll(tasks); return 0; } }")
    assert dynamic["total_ms"] is None
