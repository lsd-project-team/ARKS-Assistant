"""返回Task不是已完成；async调用者只先执行首个未完成await之前的代码。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("methods", "body", "expected"),
    [
        (
            "Task Start(){return Task.Run(()=>Thread.Sleep(20));}",
            "var task=Start();Thread.Sleep(5);task.Wait();Thread.Sleep(3);",
            23,
        ),
        (
            "Task Start(){return Task.Delay(20);}",
            "var task=Start();Thread.Sleep(5);task.Wait();Thread.Sleep(3);",
            23,
        ),
        (
            "Task Start(){Thread.Sleep(3);return Task.Delay(20);}",
            "var task=Start();Thread.Sleep(5);task.Wait();Thread.Sleep(7);",
            30,
        ),
        (
            "Task Start()=>Make();Task Make(){Thread.Sleep(3);return Task.Delay(20);}",
            "var task=Start();Thread.Sleep(5);task.GetAwaiter().GetResult();Thread.Sleep(7);",
            30,
        ),
        (
            "Task Start(){Thread.Sleep(3);return Task.CompletedTask;}",
            "var task=Start();Thread.Sleep(5);task.Wait();Thread.Sleep(7);",
            15,
        ),
        ("Task Start(){return Task.Run(()=>Thread.Sleep(20));}", "Start();Thread.Sleep(3);", 3),
        (
            "Task Start()=>new Task(()=>Thread.Sleep(20));",
            "var task=Start();Thread.Sleep(3);task.Start();task.Wait();",
            23,
        ),
        (
            "void Join(Task task){Thread.Sleep(3);task.Wait();}",
            "var task=Task.Delay(20);Thread.Sleep(5);Join(task);",
            20,
        ),
        (
            "Task task;void Start(){task=Task.Delay(20);}",
            "Start();Thread.Sleep(5);task.Wait();",
            20,
        ),
        ("", "var task=Task.Delay(20);Action join=()=>task.Wait();Thread.Sleep(5);join();", 20),
        (
            "Task<int> Start()=>Task.FromResult(7);",
            "var value=await Start();Thread.Sleep(value);",
            7,
        ),
        (
            "Task<int> Start(){Thread.Sleep(3);return Task.FromResult(7);}",
            "var value=Start().Result;Thread.Sleep(value);",
            10,
        ),
        (
            "async Task<int> Start(){await Task.Delay(5);return 7;}",
            "var value=await Start();Thread.Sleep(value);",
            12,
        ),
        (
            "async Task Start(){Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);}",
            "var task=Start();Thread.Sleep(5);task.Wait();Thread.Sleep(7);",
            32,
        ),
        (
            "async Task Start(){Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);}",
            "Start();Thread.Sleep(7);",
            10,
        ),
        (
            "async Task Start(){Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);}",
            "await Start();Thread.Sleep(7);",
            32,
        ),
        (
            "async Task Start(){Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);"
            "await Task.Delay(10);Thread.Sleep(4);}",
            "var task=Start();Thread.Sleep(5);task.Wait();Thread.Sleep(7);",
            46,
        ),
        (
            "async Task Start(){Thread.Sleep(3);await Task.Delay(0);Thread.Sleep(2);}",
            "var task=Start();Thread.Sleep(7);task.Wait();",
            12,
        ),
        (
            "async Task Start(){try{await Task.Delay(20);}finally{Thread.Sleep(3);}}",
            "var task=Start();Thread.Sleep(5);task.Wait();Thread.Sleep(7);",
            30,
        ),
        ("Task Start()=>Task.Delay(20);", "Task.Run(Start).Wait();Thread.Sleep(3);", 23),
        (
            "",
            "Func<Task> cb=async()=>{Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);};"
            "var t=cb();Thread.Sleep(5);t.Wait();Thread.Sleep(7);",
            32,
        ),
        ("", "Func<Task> cb=()=>Task.Delay(20);cb();Thread.Sleep(3);", 3),
        ("", "Func<Task> cb=()=>Task.Delay(20);await cb();Thread.Sleep(3);", 23),
        (
            "",
            "Func<Task> cb=async()=>{Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);};"
            "cb();Thread.Sleep(7);",
            10,
        ),
        (
            "Task Start()=>Task.Delay(20);",
            "Func<Task> cb=Start;var t=cb();Thread.Sleep(5);t.Wait();",
            20,
        ),
        (
            "async Task Start(){Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(2);}",
            "Task.Run(Start).Wait();Thread.Sleep(7);",
            32,
        ),
        (
            "async Task Start(){await Inner();Thread.Sleep(2);}"
            "async Task Inner(){Thread.Sleep(3);await Task.Delay(20);Thread.Sleep(4);}",
            "var t=Start();Thread.Sleep(5);t.Wait();Thread.Sleep(7);",
            36,
        ),
        (
            "async Task<int> Start(){try{return 7;}finally{await Task.Delay(20);Thread.Sleep(3);}}",
            "var value=await Start();Thread.Sleep(value);",
            30,
        ),
        (
            "async Task Start(){for(int i=0;i<3;i++){Thread.Sleep(2);await Task.Delay(10);}}",
            "var t=Start();Thread.Sleep(5);t.Wait();",
            36,
        ),
        (
            "Task Start(){if(option)return Task.Delay(20);return Task.Delay(30);}",
            "var t=Start();Thread.Sleep(40);t.Wait();",
            40,
        ),
        (
            "",
            "var tasks=new System.Collections.Generic.List<Task>();"
            "tasks.Add(Task.Delay(20));tasks.Add(Task.Delay(30));"
            "Thread.Sleep(5);Task.WaitAll(tasks.ToArray());",
            30,
        ),
        (
            "",
            "var a=Task.Delay(20);var b=Task.Delay(30);await Task.WhenAll(a,b);Thread.Sleep(3);",
            33,
        ),
        (
            "Task<int> Start()=>Task.FromResult(7);",
            "var value=Start().GetAwaiter().GetResult();Thread.Sleep(value/2);",
            3,
        ),
    ],
)
def test_returned_task_creation_and_completion_timeline(methods, body, expected):
    result = analyze(f"class Demo {{{methods}public int DoWork(){{{body}return 0;}}}}")
    assert result["total_ms"] == expected
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected


def test_unknown_returned_task_keeps_completion_unresolved():
    result = analyze("""class Demo {Task Start(){Thread.Sleep(5);return ExternalTask();}
        public int DoWork(){var task=Start();task.Wait();Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] is None and result["known_delay_max_ms"] is None
    assert result["known_delay_min_ms"] >= 8


def test_async_continuation_does_not_publish_a_future_value_as_a_current_constant():
    result = analyze("""class Demo {int delay=5;
        async Task Start(){await Task.Delay(20);delay=999;}
        public int DoWork(){Start();Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert not any(s.get("milliseconds") == 999 and not s["background"] for s in result["stages"])


def test_immediately_awaited_async_call_applies_completed_state_before_the_next_delay():
    result = analyze("""class Demo {int delay=5;
        async Task Start(){delay=7;await Task.Delay(20);delay=9;}
        public int DoWork(){await Start();Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 29


@pytest.mark.parametrize("expression", ["await Start().ConfigureAwait(false)", "Start().Result"])
def test_completed_task_effects_pass_through_framework_wait_wrappers(expression):
    result = analyze(f"""class Demo {{int delay=5;
        async Task<int> Start(){{delay=7;await Task.Delay(20);delay=9;return 1;}}
        public int DoWork(){{var value={expression};Thread.Sleep(delay);return 0;}}}}""")
    assert result["total_ms"] == 29


def test_task_values_remain_internal_to_the_report():
    import json

    result = analyze("""class Demo {Task<int> pending=Task.FromResult(7);
        public int DoWork(){pending=Task.FromResult(9);
        Thread.Sleep(this.pending.Result);return 0;}}""")
    assert result["total_ms"] == 9
    json.dumps(result)


@pytest.mark.parametrize(
    "read", ["await Start()", "Start().Result", "Start().GetAwaiter().GetResult()"]
)
def test_task_result_keeps_the_source_numeric_type_for_overload_binding(read):
    result = analyze(f"""class Demo {{Task<int> Start()=>Task.FromResult(7);
        void Pause(int value){{Thread.Sleep(value/2);}}
        void Pause(double value){{Thread.Sleep(999);}}
        public int DoWork(){{var value={read};Pause(value);return 0;}}}}""")
    assert result["total_ms"] == 3
    assert not any(stage.get("milliseconds") == 999 for stage in result["stages"])


def test_source_task_method_group_join_publishes_completed_writes():
    result = analyze("""class Demo {int delay=5;
        async Task Start(){await Task.Delay(20);delay=9;}
        public int DoWork(){Task.Run(Start).Wait();Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 29


@pytest.mark.parametrize(
    "wait", ["Start().Wait()", "Start().GetAwaiter().GetResult()", "await Start()"]
)
@pytest.mark.parametrize(
    "implementation",
    [
        "async Task Start(){await Task.Delay(20);delay=9;}",
        "Task Start()=>Inner();async Task Inner(){await Task.Delay(20);delay=9;}",
        "Task Start()=>Task.Run(()=>{Thread.Sleep(20);delay=9;});",
    ],
)
def test_fresh_source_task_join_applies_its_completed_state(wait, implementation):
    result = analyze(f"""class Demo {{int delay=5;{implementation}
        public int DoWork(){{{wait};Thread.Sleep(delay);return 0;}}}}""")
    assert result["total_ms"] == 29


def test_forwarding_an_old_task_does_not_replay_its_past_writes():
    result = analyze("""class Demo {int delay=5;
        async Task Start(){await Task.Delay(20);delay=9;}
        Task Same(Task task)=>task;
        public int DoWork(){var t=Start();Thread.Sleep(30);delay=7;
            Same(t).Wait();Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 37


@pytest.mark.parametrize(
    "body",
    [
        "await Task.Run(()=>Thread.Sleep(20));",
        "var t=Task.Run(()=>Thread.Sleep(20));Thread.Sleep(5);t.Wait();",
        "await Start();",
        "Start().GetAwaiter().GetResult();",
    ],
)
def test_joined_task_work_is_shown_as_part_of_the_waited_action(body):
    result = analyze(f"""class Demo {{async Task Start(){{await Task.Delay(10);Thread.Sleep(20);}}
        public int DoWork(){{{body}return 0;}}}}""")
    delays = [
        stage
        for stage in result["stages"]
        if stage.get("milliseconds") == 20 and stage["kind"] == "delay"
    ]
    assert len(delays) == 1 and not delays[0]["background"]


def test_waiting_on_an_async_parent_keeps_its_unjoined_child_in_the_background():
    result = analyze("""class Demo {async Task Start(){await Task.Delay(10);
        Task.Run(()=>Thread.Sleep(999));Thread.Sleep(20);}
        public int DoWork(){await Start();return 0;}}""")
    assert result["total_ms"] == 30
    assert any(
        stage.get("milliseconds") == 999 and stage["background"] for stage in result["stages"]
    )
    assert any(
        stage.get("milliseconds") == 20 and not stage["background"] for stage in result["stages"]
    )


def test_an_unjoined_async_parent_does_not_promote_the_task_it_will_await_later():
    result = analyze("""class Demo {async Task Start(Task task){await Task.Delay(10);await task;}
        public int DoWork(){var t=Task.Run(()=>Thread.Sleep(20));Start(t);return 0;}}""")
    assert result["total_ms"] == 0
    assert all(stage["background"] for stage in result["stages"] if stage.get("milliseconds") == 20)


def test_joining_an_async_parent_also_joins_its_existing_task_dependency():
    result = analyze("""class Demo {async Task Start(Task task){await Task.Delay(10);await task;}
        public int DoWork(){var t=Task.Run(()=>Thread.Sleep(20));await Start(t);return 0;}}""")
    assert result["total_ms"] == 20
    assert any(
        stage.get("milliseconds") == 20 and not stage["background"] for stage in result["stages"]
    )
