"""消费查询才执行回调，短路只读所需输入；foreach正文与查询逐项交错。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze
from tests.unit.test_source_timing_eager_collections import listing


@pytest.mark.parametrize(
    "body,expected",
    [
        (
            "int count=new[]{1,2,3}.Where(n=>{Thread.Sleep(2);return n>1;}).Count();"
            "Thread.Sleep(count);",
            8,
        ),
        (
            "int count=new[]{1,2,3}.Select(n=>{Thread.Sleep(n);return n;}).Count();"
            "Thread.Sleep(count);",
            9,
        ),
        (
            "if(new[]{1,2,3}.Any(n=>{Thread.Sleep(n);return n>1;}))Thread.Sleep(7);",
            10,
        ),
        (
            "if(new[]{1,2,3}.Where(n=>{Thread.Sleep(2);return n>1;}).Any())Thread.Sleep(7);",
            11,
        ),
        (
            "int first=new[]{2,3}.Select(n=>{Thread.Sleep(n);return n*2;}).First();"
            "Thread.Sleep(first);",
            6,
        ),
        (
            "int first=new[]{2,3,5}.First(n=>{Thread.Sleep(n);return n>2;});Thread.Sleep(first);",
            8,
        ),
        (
            "int last=new[]{1,2,3}.Where(n=>{Thread.Sleep(3);return n>1;})"
            ".Select(n=>{Thread.Sleep(n);return n;}).Last();Thread.Sleep(last);",
            17,
        ),
        (
            "if(!new[]{1,2,3}.All(n=>{Thread.Sleep(n);return n<2;}))Thread.Sleep(7);",
            10,
        ),
        ("Thread.Sleep(new int[0].FirstOrDefault()+2);", 2),
        ("Thread.Sleep(new int[0].LastOrDefault()+2);", 2),
        ("if(!new int[0].Any())Thread.Sleep(7);", 7),
        ("if(new int[0].All(n=>{Thread.Sleep(99);return false;}))Thread.Sleep(7);", 7),
        (
            "Thread.Sleep(System.Linq.Enumerable.Count(new[]{2,3},"
            "n=>{Thread.Sleep(n);return n>2;}));",
            6,
        ),
        (
            "int delay=1;foreach(var n in new[]{1,2}.Select(n=>{Thread.Sleep(delay);return n;}))"
            "{delay++;Thread.Sleep(n);}",
            6,
        ),
        (
            "foreach(var n in new[]{2,3}.Select(n=>{Thread.Sleep(n);return n;}))"
            "{Thread.Sleep(7);break;}",
            9,
        ),
        (
            "var source=new[]{2,3};foreach(var n in source.Select(n=>{Thread.Sleep(n);return n;}))"
            "{if(n==2)source[1]=7;}",
            9,
        ),
        (
            "foreach(var n in new[]{1,2,3}.Where(n=>{Thread.Sleep(2);return n>1;}))"
            "{Thread.Sleep(n);break;}",
            6,
        ),
        (
            "foreach(var n in new[]{1,2,3}.Select(n=>{Thread.Sleep(n);return n;}))"
            "{if(n==2)return 0;}Thread.Sleep(999);",
            3,
        ),
        (
            "foreach(var n in new[]{1,2,3}.Where(n=>{Thread.Sleep(2);return true;}))"
            "{if(n==2)continue;Thread.Sleep(n);}",
            10,
        ),
    ],
)
def test_query_consumers_keep_evaluation_order_short_circuits_and_values(body, expected):
    assert listing(body)["total_ms"] == expected


@pytest.mark.parametrize("operation", ["First", "Last"])
def test_empty_required_element_stops_the_callers_success_path(operation):
    result = listing(f"new int[0].{operation}();Thread.Sleep(999);")
    assert result["execution_status"] == "unavailable" and result["total_ms"] is None
    assert not any(s.get("milliseconds") == 999 for s in result["stages"])


def test_first_member_type_resolves_the_next_source_call():
    result = listing(
        "new[]{new Item()}.Where(n=>true).First().Wait();",
        "class Item{public void Wait(){Thread.Sleep(7);}}",
    )
    assert result["total_ms"] == 7


def test_consumer_bool_return_type_selects_the_correct_source_overload():
    result = analyze("""using System.Linq;class Demo{
        void Pause(bool value){Thread.Sleep(7);}void Pause(int value){Thread.Sleep(999);}
        public int DoWork(){Pause(new[]{2,3}.Any());return 0;}}""")
    assert result["total_ms"] == 7


def test_source_owned_any_retains_its_body_and_result():
    result = listing(
        "if(new Values().Any())Thread.Sleep(3);",
        "class Values{public bool Any(){Thread.Sleep(11);return true;}}",
    )
    assert result["total_ms"] == 14


def test_unknown_where_keeps_both_short_circuit_and_continue_paths():
    result = listing(
        "bool keep=ReadFlag();new[]{1,2}.Where(n=>{Thread.Sleep(3);return keep;})"
        ".Any();Thread.Sleep(11);"
    )
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (14, 17)


def test_unknown_count_does_not_keep_one_samples_captured_write():
    result = listing(
        "List<int> source=ReadList();int delay=2;source.Count(n=>{delay++;return true;});"
        "Thread.Sleep(delay);"
    )
    assert result["known_delay_min_ms"] == 0 and result["known_delay_max_ms"] is None


def test_short_circuit_does_not_check_list_version_after_returning_a_match():
    result = listing(
        "var source=new List<int>{2,3};if(source.Any(n=>{Thread.Sleep(n);source.Add(7);"
        "return true;}))Thread.Sleep(3);"
    )
    assert result["total_ms"] == 5


def test_continuing_enumeration_detects_list_changes_before_visiting_another_item():
    result = listing(
        "var source=new List<int>{2,3};source.Any(n=>{Thread.Sleep(n);source.Add(7);"
        "return false;});Thread.Sleep(999);"
    )
    assert result["execution_status"] == "unavailable"
    assert not any(s.get("milliseconds") == 999 for s in result["stages"])


def test_each_streamed_foreach_output_has_its_own_captured_variable():
    result = listing(
        "Action first=null;foreach(var n in new[]{2,3}.Select(n=>n))"
        "{if(n==2)first=()=>Thread.Sleep(n);}first();"
    )
    assert result["total_ms"] == 2


def test_failed_receiver_does_not_execute_outer_arguments_or_the_later_statement():
    result = analyze("""using System.Linq;class Item{public void Wait(int n){Thread.Sleep(n);}}
        class Demo{int Later(){Thread.Sleep(999);return 2;}public int DoWork(){
        new Item[0].First().Wait(Later());Thread.Sleep(777);return 0;}}""")
    assert result["execution_status"] == "unavailable"
    assert not any(s.get("milliseconds") in {999, 777} for s in result["stages"])


def test_failed_first_argument_stops_later_argument_evaluation():
    result = analyze("""using System.Linq;class Demo{
        int Later(){Thread.Sleep(999);return 2;}void Work(int x,int y){Thread.Sleep(777);}
        public int DoWork(){Work(new int[0].First(),Later());return 0;}}""")
    assert result["execution_status"] == "unavailable"
    assert not any(s.get("milliseconds") in {999, 777} for s in result["stages"])


def test_terminal_named_arguments_follow_source_and_predicate_names():
    result = listing(
        "Thread.Sleep(Enumerable.Count(predicate:n=>{Thread.Sleep(n);return n>2;},"
        "source:new[]{2,3}));"
    )
    assert result["total_ms"] == 6


def test_multiple_consumers_evaluate_the_same_deferred_query_again():
    result = listing(
        "var query=new[]{2,3}.Select(n=>{Thread.Sleep(n);return n;});query.Any();query.Last();"
    )
    assert result["total_ms"] == 7


def test_empty_first_in_a_constructor_argument_skips_constructor_side_effects():
    result = listing(
        "new Item(new int[0].First());Thread.Sleep(777);",
        "class Item{public Item(int n){Thread.Sleep(999);}}",
    )
    assert result["execution_status"] == "unavailable"
    assert not any(s.get("milliseconds") in {999, 777} for s in result["stages"])


def test_long_count_and_last_predicate_evaluate_all_required_items():
    result = listing(
        "Thread.Sleep((int)new[]{1,2,3}.LongCount(n=>{Thread.Sleep(2);return n>1;}));"
        "Thread.Sleep(new[]{2,3,5}.LastOrDefault(n=>{Thread.Sleep(n);return n<5;}));"
    )
    assert result["total_ms"] == 21


def test_named_static_first_retains_its_element_type_for_following_source_calls():
    result = listing(
        "Enumerable.First(predicate:n=>true,source:new[]{new Item()}).Wait();",
        "class Item{public void Wait(){Thread.Sleep(7);}}",
    )
    assert result["total_ms"] == 7


def test_callback_expansion_limit_does_not_make_query_count_a_known_zero(monkeypatch):
    from app.modules.action_timing import source_budget

    monkeypatch.setattr(source_budget, "MAX_CALL_DEPTH", 7)
    chain = "".join(f"int A{i}(){{return A{i + 1}();}}" for i in range(5))
    result = analyze(
        "using System.Linq;class Demo{"
        + chain
        + "int A5(){return new[]{2,3}.Select(n=>n).Count();}"
        "public int DoWork(){Thread.Sleep(A0());return 0;}}"
    )
    delays = [s for s in result["stages"] if s["kind"] == "delay"]
    assert result["truncated"] and result["total_ms"] is None
    assert delays and delays[-1]["milliseconds"] is None
