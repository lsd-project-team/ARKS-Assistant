"""已知重复调用必须完整计算；共享工作预算仍限制单动作分析资源。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


def limited(source, limit):
    from app.modules.action_timing.source_budget import CallBudget
    from app.modules.action_timing.source_estimator import Estimator
    from app.modules.action_timing.source_index import SourceIndex

    index = SourceIndex([{"path": "main.cs", "content": source, "version": "fixture"}])
    estimator = Estimator(index)
    estimator.budget = CallBudget(limit=limit)
    return estimator, estimator.estimate(index.by_method[("Demo", "DoWork")][0])


@pytest.mark.parametrize(
    "loop",
    [
        "for(int n=0;n<50;n++)A(n);",
        "foreach(var n in Enumerable.Range(0,50))A(n);",
        "int n=0;while(n<50){A(n);n++;}",
        "Enumerable.Range(0,50).ToList().ForEach(n=>A(n));",
        "Enumerable.Range(0,50).Select(n=>A(n)).ToList();",
    ],
)
def test_known_repeated_source_calls_do_not_lose_the_later_iterations(loop):
    result = analyze(
        "using System.Linq;class Demo{int A(int n){return B(n);}int B(int n){return C(n);}"
        "int C(int n){Thread.Sleep(n+1);return n;}public int DoWork(){" + loop + "return 0;}}"
    )
    assert result["total_ms"] == 1275
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 1275


def test_repeated_call_shared_writes_are_not_replaced_with_one_cached_result():
    result = analyze("""class Demo{int delay=1;void A(){B();}void B(){C();}
        void C(){Thread.Sleep(delay++);}public int DoWork(){
        for(int n=0;n<50;n++)A();Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 1326


def test_recursive_source_call_still_preserves_an_unknown_completion_time():
    result = analyze("""class Demo{void A(){Thread.Sleep(2);A();}
        public int DoWork(){A();return 0;}}""")
    assert result["truncated"] and result["total_ms"] is None


def test_total_call_protection_preserves_mandatory_literal_waits_without_more_calls():
    estimator, result = limited(
        """class Demo{void Leaf(){Thread.Sleep(3);}
        public int DoWork(){for(int i=0;i<10;i++)Leaf();return 0;}}""",
        4,
    )
    assert estimator.budget.used == 4
    assert result["known_delay_min_ms"] == 30 and result["known_delay_max_ms"] is None
    assert result["truncated"] and result["total_ms"] is None


def test_query_iteration_cannot_bypass_the_shared_action_protection():
    estimator, result = limited(
        """using System.Linq;class Demo{public int DoWork(){
        new[]{1,2,3,4,5}.Select(n=>{Thread.Sleep(3);return n;}).ToList();return 0;}}""",
        3,
    )
    assert estimator.budget.used == 3
    assert result["known_delay_min_ms"] == 9 and result["known_delay_max_ms"] is None
    assert result["truncated"] and result["total_ms"] is None


def test_parallel_probe_copies_share_one_action_call_protection():
    estimator, result = limited(
        """using System.Threading.Tasks;class Demo{
        void Leaf(){Thread.Sleep(3);}public int DoWork(){
        Parallel.ForEach(new[]{1,2,3,4},n=>Leaf());return 0;}}""",
        3,
    )
    assert estimator.budget.used == 3
    assert result["truncated"] and result["total_ms"] is None


def test_asynchronous_delegate_reset_does_not_reset_the_shared_action_protection():
    estimator, result = limited(
        """using System;class Demo{void Leaf(){Thread.Sleep(3);}
        public int DoWork(){Action callback=()=>Leaf();
        var first=callback.BeginInvoke(null,null);callback.EndInvoke(first);
        var second=callback.BeginInvoke(null,null);callback.EndInvoke(second);return 0;}}""",
        3,
    )
    assert estimator.budget.used == 3
    assert result["truncated"] and result["total_ms"] is None


@pytest.mark.parametrize(
    "call",
    [
        "Inner();",
        "Action work=Inner;work();",
        "Action work=Inner;var pending=work.BeginInvoke(null,null);work.EndInvoke(pending);",
    ],
)
@pytest.mark.parametrize(
    "loop",
    [
        "for(int n=0;n<20;n++)Thread.Sleep(100);",
        "foreach(var n in Enumerable.Range(0,20))Thread.Sleep(100);",
        "int n=0;while(n<20){Thread.Sleep(100);n++;}",
        "Enumerable.Range(0,20).ToList().ForEach(n=>Thread.Sleep(100));",
        "Enumerable.Range(0,20).Select(n=>{Thread.Sleep(100);return n;}).ToList();",
    ],
)
def test_deep_unknown_loops_do_not_hide_the_callers_known_delay_iterations(call, loop):
    result = analyze(
        """using System;using System.Collections.Generic;using System.Linq;class Demo{
        extern bool Ready();void Inner(){for(int batch=0;batch<5;batch++){
        var seen=new List<int>();while(true){seen.Add(1);Thread.Sleep(1);if(Ready())break;}}}
        public int DoWork(){"""
        + call
        + loop
        + "return 0;}}"
    )
    assert result["known_delay_min_ms"] >= 2000
    assert result["total_ms"] is None
    assert (
        sum(
            stage["kind"] == "delay"
            and stage.get("milliseconds") == 100
            and not stage["background"]
            and not stage.get("repeat")
            for stage in result["stages"]
        )
        == 20
    )


def limited_iterations(source, limit):
    from app.modules.action_timing.source_budget import IterationBudget
    from app.modules.action_timing.source_estimator import Estimator
    from app.modules.action_timing.source_index import SourceIndex

    index = SourceIndex([{"path": "main.cs", "content": source, "version": "fixture"}])
    estimator = Estimator(index)
    estimator.iteration_budget = IterationBudget(limit=limit)
    return estimator, estimator.estimate(index.by_method[("Demo", "DoWork")][0])


def test_iteration_protection_is_shared_across_source_method_bodies():
    estimator, result = limited_iterations(
        """class Demo{void Part(){for(int i=0;i<3;i++)Thread.Sleep(1);}
        public int DoWork(){Part();Part();Thread.Sleep(7);return 0;}}""",
        4,
    )
    assert estimator.iteration_budget.used == 4
    assert result["known_delay_min_ms"] == 11
    assert result["truncated"] and result["total_ms"] is None


@pytest.mark.parametrize(
    "source",
    [
        """using System.Threading.Tasks;class Demo{public int DoWork(){
        Parallel.ForEach(new[]{1,2},n=>{for(int i=0;i<3;i++)Thread.Sleep(1);});return 0;}}""",
        """using System;class Demo{void Part(){for(int i=0;i<3;i++)Thread.Sleep(1);}
        public int DoWork(){Action work=Part;var first=work.BeginInvoke(null,null);
        work.EndInvoke(first);var second=work.BeginInvoke(null,null);work.EndInvoke(second);
        return 0;}}""",
    ],
)
def test_parallel_and_async_frames_cannot_reset_the_shared_iteration_protection(source):
    estimator, result = limited_iterations(source, 3)
    assert estimator.iteration_budget.used == 3
    assert result["truncated"] and result["total_ms"] is None
