"""嵌套任务只等待外层；Unwrap及任务结果读取再接上内层完成边界。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "Task.Factory.StartNew(async()=>{Thread.Sleep(3);await Task.Delay(20);"
            "Thread.Sleep(2);})"
            ".Unwrap().Wait();Thread.Sleep(7);",
            32,
        ),
        (
            "var outer=Task.Factory.StartNew(async()=>{Thread.Sleep(3);await Task.Delay(20);"
            "Thread.Sleep(2);});"
            "var inner=outer.GetAwaiter().GetResult();inner.Wait();Thread.Sleep(7);",
            32,
        ),
        (
            "Task.Factory.StartNew(async()=>{Thread.Sleep(3);await Task.Delay(20);"
            "Thread.Sleep(2);})"
            ".Result.Wait();Thread.Sleep(7);",
            32,
        ),
        ("var value=Task.Run(()=>{Thread.Sleep(3);return 7;}).Result;Thread.Sleep(value);", 10),
        ("Task.Run((Action)(()=>Task.Delay(20))).Wait();Thread.Sleep(7);", 7),
    ],
)
def test_nested_task_and_explicit_action_completion(body, expected):
    result = analyze(f"class Demo {{public int DoWork(){{{body}return 0;}}}}")
    assert result["total_ms"] == expected


def test_equal_duration_branch_tasks_keep_both_waited_stage_paths():
    result = analyze("""class Demo {Task Start(){if(option)return Task.Run(()=>Thread.Sleep(20));
        else return Task.Run(()=>Thread.Sleep(20));}
        public int DoWork(){await Start();return 0;}}""")
    assert result["total_ms"] == 20
    delays = [
        stage
        for stage in result["stages"]
        if stage["kind"] == "delay" and stage.get("milliseconds") == 20
    ]
    assert len(delays) == 2 and all(not stage["background"] for stage in delays)


def test_merged_old_tasks_do_not_replay_completed_shared_writes():
    result = analyze("""class Demo {int delay=5;async Task Work(){await Task.Delay(20);delay=9;}
        Task Same(Task a,Task b){if(option)return a;else return b;}
        public int DoWork(){var a=Work();var b=Work();Thread.Sleep(30);delay=7;
            Same(a,b).Wait();Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 37


@pytest.mark.parametrize(
    "join", ["Task.Run(()=>task).Wait()", "Task.Factory.StartNew(()=>task).Unwrap().Wait()"]
)
def test_task_wrappers_do_not_repeat_the_inner_tasks_old_writes(join):
    result = analyze(f"""class Demo {{int delay=5;async Task Work(){{await Task.Delay(20);delay=9;}}
        public int DoWork(){{var task=Work();Thread.Sleep(30);delay=7;
        {join};Thread.Sleep(delay);return 0;}}}}""")
    assert result["total_ms"] == 37


def test_unwrapped_fresh_task_can_publish_its_completed_state():
    result = analyze("""class Demo {int delay=5;public int DoWork(){
        await Task.Factory.StartNew(async()=>{await Task.Delay(20);delay=9;}).Unwrap();
        Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 29
