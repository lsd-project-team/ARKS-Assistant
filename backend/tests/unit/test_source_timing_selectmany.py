"""按真实扫描条件与集合展开顺序计算，提前退出不预执行剩余输入。"""

import pytest

from tests.unit.test_source_timing_eager_collections import listing


@pytest.mark.parametrize(
    "items,expected",
    [
        ("", 5),
        ("new Point{X=0,Y=0}", 5),
        ("new Point{X=0,Y=0},new Point{X=0,Y=0}", 9),
        ("new Point{X=1,Y=2},new Point{X=3,Y=4}", 5),
    ],
)
def test_scan_completed_condition_flattens_both_coordinates(items, expected):
    declarations = "class Point{public double X{get;set;}public double Y{get;set;}}"
    body = "var data=new List<Point>{" + items + "};"
    body += (
        "if(data.SelectMany(p=>new double[]{p.X,p.Y}).Count(v=>v==0)<3)"
        "Thread.Sleep(5);else Thread.Sleep(9);"
    )
    assert listing(body, declarations)["total_ms"] == expected


@pytest.mark.parametrize(
    "body,expected",
    [
        ("new[]{1,2}.SelectMany(n=>new[]{n,n+1}).ToList().ForEach(n=>Thread.Sleep(n));", 8),
        ("var q=new[]{1,2}.SelectMany(n=>{Thread.Sleep(99);return new[]{n};});Thread.Sleep(2);", 2),
        ("Thread.Sleep(new[]{1,2}.SelectMany(n=>new int[0]).Count()+2);", 2),
        (
            "Thread.Sleep(new int[0].SelectMany(n=>{Thread.Sleep(99);return new[]{n};})"
            ".Count()+2);",
            2,
        ),
        (
            "new[]{1,2}.SelectMany(n=>{Thread.Sleep(5);return new[]{n,n+1};},"
            "(outer,inner)=>{Thread.Sleep(2);return outer*10+inner;})"
            ".ToList().ForEach(n=>Thread.Sleep(n));",
            86,
        ),
        (
            "Thread.Sleep(new[]{2,3}.SelectMany(n=>{Thread.Sleep(n);return new[]{n,n+1};})"
            ".First());",
            4,
        ),
        (
            "if(new[]{1,2}.SelectMany(n=>{Thread.Sleep(n);return new[]{n,n+1};})"
            ".Any(v=>{Thread.Sleep(v);return v>1;}))Thread.Sleep(7);",
            11,
        ),
        (
            "foreach(var v in new[]{2,3}.SelectMany(n=>{Thread.Sleep(n);return new[]{n,n+1};}))"
            "{Thread.Sleep(7);break;}",
            9,
        ),
        (
            "foreach(var v in new[]{2,3}.SelectMany(n=>{Thread.Sleep(n);return new[]{n,n+1};}))"
            "{Thread.Sleep(7);return 0;}Thread.Sleep(999);",
            9,
        ),
        (
            "foreach(var v in new[]{2,3}.SelectMany(n=>{Thread.Sleep(n);return new[]{n,n+1};}))"
            "{if(v==2)continue;Thread.Sleep(v);}",
            15,
        ),
        (
            "int delay=1;foreach(var v in new[]{1,2}.SelectMany(n=>"
            "{Thread.Sleep(delay++);return new[]{n,n};}))"
            "Thread.Sleep(delay++);",
            21,
        ),
        (
            "foreach(var v in new[]{1,2}.SelectMany(n=>{Thread.Sleep(n);return new[]{n,n+1}"
            ".Select(v=>{Thread.Sleep(v);return v;});})){Thread.Sleep(7);break;}",
            9,
        ),
    ],
)
def test_flattening_is_lazy_streamed_and_preserves_result_projection(body, expected):
    assert listing(body)["total_ms"] == expected


@pytest.mark.parametrize(
    "body,expected",
    [
        (
            "int d=1;Enumerable.SelectMany(selector:n=>{Thread.Sleep(d++);return new[]{n};},"
            "source:new[]{2,3}).Count();Thread.Sleep(d);",
            6,
        ),
        (
            "Enumerable.SelectMany(resultSelector:(o,i)=>{Thread.Sleep(2);return o+i;},"
            "source:new[]{1,2},collectionSelector:o=>new[]{o}).ToList().ForEach(n=>Thread.Sleep(n));",
            10,
        ),
        (
            "new[]{1,2}.SelectMany(n=>new[]{n},(o,i)=>new{Outer=o,Inner=i}).ToList();Thread.Sleep(2);",
            2,
        ),
        (
            "var a=new List<int>{1,2};Thread.Sleep(a.SelectMany(n=>"
            "{a.Add(3);return new[]{n};}).First());",
            1,
        ),
    ],
)
def test_flattening_preserves_named_binding_and_source_short_circuit(body, expected):
    assert listing(body)["total_ms"] == expected


@pytest.mark.parametrize(
    "body",
    [
        "var a=new List<int>{1,2};a.SelectMany(n=>{a.Add(3);return new[]{n};}).Count();",
        "var a=new List<int>{1,2};new[]{0}.SelectMany(n=>a)"
        ".Select(v=>{a.Add(3);return v;}).Count();",
        "new[]{1}.SelectMany(n=>{Thread.Sleep(2);throw new Exception();return new[]{n};}).Count();",
        "new[]{1}.SelectMany(n=>new[]{n},(o,i)=>{throw new Exception();return i;}).Count();",
        "new int[0].SelectMany((Func<int,int[]>)null).Count();",
        "new[]{1}.SelectMany(n=>new[]{n},(Func<int,int,int>)null).Count();",
        "new[]{1}.SelectMany(n=>(int[])null).Count();",
        "new[]{1}.SelectMany(n=>{Thread.Sleep(2);return (int[])null;}).Count();",
    ],
)
def test_proven_flattening_failure_does_not_execute_success_tail(body):
    result = listing(body + "Thread.Sleep(999);")
    assert result["total_ms"] is None
    assert not any(
        stage["kind"] == "delay" and stage["milliseconds"] == 999 for stage in result["stages"]
    )


def test_unbound_result_selector_is_not_silently_omitted():
    declarations = "class Callbacks{public static Func<int,int,int> Project;}"
    result = listing(
        "Thread.Sleep(new[]{1}.SelectMany(n=>new[]{n},Callbacks.Project).Count()+1);", declarations
    )
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


def test_unknown_inner_length_does_not_become_an_empty_count():
    declarations = "class Data{public static int[] Values;}"
    result = listing("Thread.Sleep(new[]{1}.SelectMany(n=>Data.Values).Count()+1);", declarations)
    assert result["total_ms"] is None and result["known_delay_max_ms"] is None


def test_nested_flattening_preserves_early_break_at_all_levels():
    result = listing(
        "foreach(var v in new[]{1,2}.SelectMany(n=>new[]{n,n+1})"
        ".SelectMany(n=>{Thread.Sleep(n);return new[]{n,n+1};})){Thread.Sleep(7);break;}"
    )
    assert result["total_ms"] == 8


def test_flattening_clock_overlaps_an_already_started_task():
    result = listing(
        "var pending=Task.Delay(10);new[]{1}.SelectMany(n=>{Thread.Sleep(2);return new[]{1,2};},"
        "(o,i)=>{Thread.Sleep(3);return i;}).ToList();pending.Wait();Thread.Sleep(7);"
    )
    assert result["total_ms"] == 17


def test_unknown_result_selector_does_not_clear_known_empty_input_count():
    result = listing(
        "Thread.Sleep(new int[0].SelectMany(n=>new[]{n},Callbacks.Project).Count()+2);",
        "class Callbacks{public static Func<int,int,int> Project;}",
    )
    assert result["total_ms"] == 2


def test_large_inner_sequence_remains_bounded_without_inventing_a_full_count():
    result = listing("Thread.Sleep(new[]{0}.SelectMany(n=>Enumerable.Range(0,1000)).Count()+1);")
    assert result["truncated"] and result["total_ms"] is None


def test_source_owned_selectmany_is_not_treated_as_framework_flattening():
    declarations = (
        "class Own{public Own SelectMany(Func<int,int[]> selector){Thread.Sleep(3);return this;}}"
    )
    result = listing(
        "new Own().SelectMany(n=>{Thread.Sleep(999);return new[]{n};});Thread.Sleep(2);",
        declarations,
    )
    assert result["total_ms"] == 5


def test_result_projection_stops_with_the_first_requested_inner_item():
    result = listing(
        "Thread.Sleep(new[]{1,2}.SelectMany(n=>{Thread.Sleep(n);return new[]{n,n+1};},"
        "(o,i)=>{Thread.Sleep(3);return i;}).First());"
    )
    assert result["total_ms"] == 5


def test_unknown_filter_before_flattening_does_not_produce_a_known_count():
    result = listing(
        "Thread.Sleep(new[]{1,2}.Where(n=>Flags.Use).SelectMany(n=>new[]{n,n}).Count()+1);"
        "Thread.Sleep(7);",
        "class Flags{public static bool Use;}",
    )
    assert result["total_ms"] is None
    delays = [stage["milliseconds"] for stage in result["stages"] if stage["kind"] == "delay"]
    assert delays == [None, 7]


def test_outer_and_inner_enumeration_share_the_action_iteration_quota():
    from tests.unit.test_source_timing_call_budget import limited_iterations

    estimator, result = limited_iterations(
        "using System.Linq;class Demo{public int DoWork(){"
        "Thread.Sleep(new[]{1,2}.SelectMany(n=>new[]{n,n+1}).Count());return 0;}}",
        3,
    )
    assert estimator.iteration_budget.used == 3
    assert result["truncated"] and result["total_ms"] is None
