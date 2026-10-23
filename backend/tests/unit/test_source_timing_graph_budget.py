"""子调用的标签直线执行不能耗尽调用者的继续路径。"""

import hashlib

import pytest

from app.modules.action_timing.source_estimator import Estimator
from app.modules.action_timing.source_index import SourceIndex
from tests.unit.test_source_timing_eager_collections import listing

HELPERS = (
    "class Helper{public static bool Retry;"
    "public static void Child(){ChildStart:;int a=0;int b=1;int c=2;int d=3;int e=4;}"
    "public static void Work(){for(int i=0;i<100;i++)Child();}}"
)


WORK = [
    "Helper.Work();",
    "Action work=Helper.Work;work();",
    "Action work=Helper.Work;var pending=work.BeginInvoke(null,null);work.EndInvoke(pending);",
    "Task.Run(Helper.Work).Wait();",
]


@pytest.mark.parametrize("work", WORK)
def test_child_label_work_keeps_the_known_delay_after_a_finite_call(work):
    result = listing("ParentStart:;" + work + "Thread.Sleep(7);", HELPERS)
    assert result["known_delay_min_ms"] == 7
    assert result["known_delay_max_ms"] == 7


@pytest.mark.parametrize("work", WORK)
@pytest.mark.parametrize(
    "tail",
    [
        "if(Helper.Retry)goto ParentStart;Thread.Sleep(7);",
        "if(Helper.Retry){if(Helper.Retry)goto ParentStart;throw new Exception();}Thread.Sleep(7);",
    ],
)
def test_child_label_work_keeps_caller_tail(work, tail):
    result = listing("ParentStart:;" + work + tail, HELPERS)
    assert any(
        stage["kind"] == "delay" and stage["milliseconds"] == 7 for stage in result["stages"]
    )
    # 重试次数及APM句柄状态未定时仍可能触发路径保护，不能要求完整动作精确为7ms。
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None or result["known_delay_max_ms"] >= 7


def estimate(body, helpers, limit):
    source = (
        "using System;using System.Threading;using System.Threading.Tasks;"
        + helpers
        + "class Demo{public int DoWork(){"
        + body
        + "return 0;}}"
    )
    index = SourceIndex(
        [
            {
                "path": "main.cs",
                "content": source,
                "version": hashlib.sha256(source.encode()).hexdigest(),
                "project": "main.cs",
            }
        ]
    )
    estimator = Estimator(index)
    estimator.jump_budget.limit = limit
    return estimator.estimate(index.by_method[("Demo", "DoWork")][0]), estimator


def test_labels_without_jump_edges_do_not_spend_the_shared_jump_budget():
    result, estimator = estimate("ParentStart:;Helper.Work();Thread.Sleep(7);", HELPERS, 0)
    assert result["total_ms"] == 7
    assert estimator.jump_budget.used == 0
    assert estimator.jump_steps > 512


@pytest.mark.parametrize(
    "body",
    [
        "Helper.Work();Helper.Work();",
        "Action work=Helper.Work;work();work();",
        "Action work=Helper.Work;var a=work.BeginInvoke(null,null);work.EndInvoke(a);"
        "var b=work.BeginInvoke(null,null);work.EndInvoke(b);",
        "Task.Run(Helper.Work).Wait();Task.Run(Helper.Work).Wait();",
        "Task.Factory.StartNew(Helper.Work).Wait();Task.Factory.StartNew(Helper.Work).Wait();",
        "Parallel.ForEach(new[]{1,2},n=>Helper.Work());",
    ],
)
def test_jump_budget_is_shared_by_nested_parallel_and_async_work(body):
    helpers = "class Helper{public static void Work(){int n=0;Again:n++;if(n<6)goto Again;}}"
    result, estimator = estimate(body + "Thread.Sleep(7);", helpers, 7)
    assert estimator.jump_budget.used == 7
    assert result["truncated"] and result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage["milliseconds"] == 7 for stage in result["stages"]
    )


def test_a_local_control_graph_limit_still_bounds_changing_retry_state(monkeypatch):
    from app.modules.action_timing import source_jumps

    monkeypatch.setattr(source_jumps, "MAX_GRAPH_STEPS", 4)
    result, _ = estimate(
        "int n=0;Again:Thread.Sleep(1);if(++n<1000)goto Again;Thread.Sleep(7);", "", 4096
    )
    assert result["truncated"] and result["total_ms"] is None
    assert sum(stage["kind"] == "delay" for stage in result["stages"]) < 1000
