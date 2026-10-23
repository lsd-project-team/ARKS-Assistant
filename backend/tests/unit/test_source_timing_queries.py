"""查询创建保持惰性；物化时按源集合、闭包当前值和逐项顺序计算。"""

import pytest

from tests.unit.test_source_timing_eager_collections import listing


@pytest.mark.parametrize(
    "body,expected",
    [
        (
            "new[]{1,2,3}.Where(n=>{Thread.Sleep(2);return n>1;})"
            ".Select(n=>{Thread.Sleep(n);return n+1;}).ToList()"
            ".ForEach(n=>Thread.Sleep(n));",
            18,
        ),
        (
            "var query=new[]{2,3}.Select(n=>{Thread.Sleep(99);return n;});Thread.Sleep(2);",
            2,
        ),
        (
            "var source=new List<int>{2,3};var query=source.Select(n=>n);"
            "source=new List<int>{99};query.ToList().ForEach(n=>Thread.Sleep(n));",
            5,
        ),
        (
            "var source=new List<int>{2,3};var query=source.Select(n=>n);"
            "source[0]=7;query.ToList().ForEach(n=>Thread.Sleep(n));",
            10,
        ),
        (
            "int delay=2;var query=new[]{1,2}.Select(n=>{Thread.Sleep(delay);return n;});"
            "delay=7;query.ToList();",
            14,
        ),
        (
            "int delay=1;new[]{1,2,3}.Where(n=>{Thread.Sleep(delay++);return n>1;})"
            ".Select(n=>{Thread.Sleep(delay++);return n;}).ToList();Thread.Sleep(delay);",
            21,
        ),
        (
            "new int[0].Where(n=>{Thread.Sleep(99);return true;})"
            ".Select(n=>{Thread.Sleep(99);return n;}).ToList();Thread.Sleep(2);",
            2,
        ),
        (
            "var query=Enumerable.Range(2,2).Select(n=>{Thread.Sleep(n);return n;});"
            "query.ToList();query.ToList();",
            10,
        ),
        (
            "System.Linq.Enumerable.ToList(System.Linq.Enumerable.Select(new[]{2,3},"
            "n=>{Thread.Sleep(n);return n;}));",
            5,
        ),
        (
            "var values=new[]{2,3}.Select(n=>{Thread.Sleep(n);return n+1;}).ToArray();"
            "foreach(var n in values)Thread.Sleep(n);",
            12,
        ),
    ],
)
def test_query_materialization_respects_deferred_evaluation_and_order(body, expected):
    assert listing(body)["total_ms"] == expected


def test_select_preserves_constructed_element_type_and_shared_references():
    result = listing(
        "var values=new[]{2,3}.Select(n=>new Item{Delay=n}).ToList();"
        "values.ForEach(n=>Thread.Sleep(n.Delay));",
        "class Item{public int Delay;}",
    )
    assert result["total_ms"] == 5


def test_unknown_framework_list_query_preserves_unrelated_fixed_point_count():
    result = listing(
        "List<int> lights=ReadLights();var points=new[]{1,2,3};"
        "lights.Where(n=>n>0).Select(n=>n+1).ToList();"
        "foreach(var p in points)Thread.Sleep(1000);"
    )
    assert result["known_delay_min_ms"] == 3000
    assert result["known_delay_max_ms"] == 3000


def test_unknown_count_invalidates_only_the_actual_callback_writes():
    result = listing(
        "List<int> lights=ReadLights();int delay=2;var points=new[]{1,2,3};"
        "lights.Select(n=>{delay++;return n;}).ToList();Thread.Sleep(delay);"
        "foreach(var p in points)Thread.Sleep(1000);"
    )
    assert result["known_delay_min_ms"] == 3000
    assert result["known_delay_max_ms"] is None


def test_unknown_predicate_does_not_make_all_selector_waits_mandatory():
    result = listing(
        "bool keep=ReadFlag();new[]{2,3}.Where(n=>keep)"
        ".Select(n=>{Thread.Sleep(7);return n;}).ToList();Thread.Sleep(11);"
    )
    assert result["known_delay_min_ms"] == 11
    assert result["known_delay_max_ms"] == 25


def test_source_owned_select_keeps_its_actual_body():
    result = listing(
        "new Values().Select(n=>n).ToList().ForEach(n=>Thread.Sleep(n));",
        "class Values{public List<int> Select(Func<int,int> f){"
        "Thread.Sleep(11);return new List<int>{3};}}",
    )
    assert result["total_ms"] == 14


def test_opaque_enumerable_query_cannot_freeze_old_receiver_members():
    result = listing(
        "new Data().Read();",
        "class Data{IEnumerable<int> items;int delay=7;public void Read(){"
        "items.Select(n=>n).ToList();Thread.Sleep(delay);}}",
    )
    assert result["known_delay_min_ms"] == 0
    assert result["total_ms"] is None


def test_bounded_query_projection_does_not_spend_the_later_source_call_budget():
    result = listing(
        "Enumerable.Range(0,100).Where(n=>true).Select(n=>n).ToList();new Data().Wait();",
        "class Data{public void Wait(){Thread.Sleep(1000);}}",
    )
    assert result["total_ms"] == 1000


def test_selected_member_type_uses_the_lambda_parameter_context():
    result = listing(
        "new[]{new Parent()}.Select(p=>p.Child).ToList().ForEach(c=>c.Wait());",
        "class Parent{public Child Child=new Child();}"
        "class Child{public void Wait(){Thread.Sleep(7);}}",
    )
    assert result["total_ms"] == 7


def test_null_selector_remains_unresolved_instead_of_crashing_type_inference():
    result = listing("Func<int,int> selector=null;new[]{1}.Select(selector).ToList();")
    assert result["total_ms"] is None
