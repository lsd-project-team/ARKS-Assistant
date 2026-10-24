"""调用受限时，保留只读私有任务身份，但不能掩盖真实写入。"""

import pytest

from tests.unit.test_source_timing_call_budget import limited


@pytest.mark.parametrize(
    "kind, callback",
    [
        ("Task", "()=>Work()"),
        ("System.Threading.Tasks.Task", "()=>Work()"),
        ("Task<int>", "()=>{Work();return 1;}"),
    ],
)
def test_read_only_refresh_does_not_discard_the_task_that_is_awaited(kind, callback):
    estimator, result = limited(
        f"""using System.Threading.Tasks;class Demo{{{kind} pending;
        string message;void Refresh(){{message="working";}}
        void Empty(){{}}void Work(){{Empty();Refresh();Thread.Sleep(3);}}
        public async Task DoWork(){{pending=Task.Run({callback});
        await pending;Thread.Sleep(7);}}}}""",
        2,
    )
    assert estimator.budget.used == 2
    assert result["known_delay_min_ms"] == 10
    assert result["total_ms"] is None and result["truncated"]
    assert any(
        stage["kind"] == "delay"
        and stage.get("milliseconds") == 3
        and not stage["background"]
        for stage in result["stages"]
    )


@pytest.mark.parametrize(
    "body",
    [
        "pending=null;",
        "Reset();",
        "Change(ref pending);",
        "External.Change(this);",
        "change();",
        "External.Change(()=>pending=null);",
    ],
)
def test_possible_task_writes_are_not_treated_as_read_only_refresh(body):
    _, result = limited(
        """using System;using System.Threading.Tasks;class Demo{Task pending;
        Action change;void Change(ref Task task){task=null;}
        void Reset(){pending=null;}void Refresh(){"""
        + body
        + """}void Empty(){}void Work(){Empty();Refresh();Thread.Sleep(3);}
        public async Task DoWork(){pending=Task.Run(()=>Work());
        await pending;Thread.Sleep(7);}}""",
        2,
    )
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "delay"
        and stage.get("milliseconds") == 3
        and stage["background"]
        for stage in result["stages"]
    )


@pytest.mark.parametrize("visibility", ["public", "protected", "internal"])
def test_an_externally_writable_task_is_not_given_private_field_protection(visibility):
    _, result = limited(
        f"""using System.Threading.Tasks;class Demo{{{visibility} Task pending;
        void Refresh(){{}}void Empty(){{}}
        void Work(){{Empty();Refresh();Thread.Sleep(3);}}
        public async Task DoWork(){{pending=Task.Run(()=>Work());
        await pending;Thread.Sleep(7);}}}}""",
        2,
    )
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "delay"
        and stage.get("milliseconds") == 3
        and stage["background"]
        for stage in result["stages"]
    )


def test_read_only_refresh_does_not_clear_an_existing_escape_invalidation():
    _, result = limited(
        """using System.Threading.Tasks;class Demo{Task pending;
        void Refresh(){}public async Task DoWork(){
        pending=Task.Run(()=>Thread.Sleep(3));External.Change(this);Refresh();
        await pending;Thread.Sleep(7);}}""",
        1,
    )
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "delay"
        and stage.get("milliseconds") == 3
        and stage["background"]
        for stage in result["stages"]
    )


def test_private_task_protection_does_not_freeze_other_fields_or_reachable_objects():
    _, result = limited(
        """using System.Threading.Tasks;class Box{public int delay=1000;}
        class Demo{Task pending;int delay=999;Box box=new Box();
        void Refresh(){delay=0;box.delay=0;}void Empty(){}
        void Work(){Empty();Refresh();Thread.Sleep(3);}
        public async Task DoWork(){pending=Task.Run(()=>Work());await pending;
        Thread.Sleep(delay);Thread.Sleep(box.delay);Thread.Sleep(7);}}""",
        2,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None
    assert not any(stage.get("milliseconds") in {999, 1000} for stage in result["stages"])
    assert any(
        stage["kind"] == "delay" and stage.get("milliseconds") is None
        for stage in result["stages"]
    )
