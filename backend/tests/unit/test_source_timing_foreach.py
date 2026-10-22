"""只枚举源码已知集合；不能假定动态集合为空或沿用修改前的元素。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("foreach(int x in new int[]{2,3,5}){Thread.Sleep(x);}", 10),
        ("var a=new[]{2,3,5};foreach(var x in a){Thread.Sleep(x);}", 10),
        ("foreach(int x in new int[3]){Thread.Sleep(x+2);}", 6),
        ("foreach(var x in new List<int>{2,3,5}){Thread.Sleep(x);}", 10),
        ("foreach(var x in Enumerable.Range(2,3)){Thread.Sleep(x);}", 9),
        ("foreach(var x in new int[]{2,3,5}){if(x==3)continue;Thread.Sleep(x);}", 7),
        ("foreach(var x in new int[]{2,3,5}){Thread.Sleep(x);if(x==3)break;}", 5),
        (
            "foreach(var x in new int[]{2,3,5}){if(x==3)return 0;Thread.Sleep(x);}"
            "Thread.Sleep(999);",
            2,
        ),
        ("int delay=1;foreach(var x in new[]{2,3}){delay=x;}Thread.Sleep(delay);", 3),
        ("foreach(var x in new int[]{}){Thread.Sleep(999);}Thread.Sleep(7);", 7),
        ("int[] a=new int[]{2,3};foreach(var x in a){a=new int[]{99};Thread.Sleep(x);}", 5),
        ("int[] a=new int[]{2,3};foreach(var x in a){a[1]=7;Thread.Sleep(x);}", 9),
        ("var a=new List<int>();a.Add(2);a.Add(3);foreach(var x in a){Thread.Sleep(x);}", 5),
    ],
)
def test_foreach_collection_elements_and_control_flow(body, expected):
    result = analyze(
        "using System.Collections.Generic;using System.Linq;"
        f"class Demo {{public int DoWork(){{{body}return 0;}}}}"
    )
    assert result["total_ms"] == expected


def test_collection_expression_runs_once_before_enumeration():
    result = analyze("""class Demo {int[] Items(){Thread.Sleep(7);return new int[]{2,3};}
        public int DoWork(){foreach(var x in Items()){Thread.Sleep(x);}return 0;}}""")
    assert result["total_ms"] == 12


def test_each_foreach_iteration_has_its_own_captured_variable():
    result = analyze("""class Demo {public int DoWork(){Action first=null;
        foreach(var x in new int[]{2,3,5}){if(x==2)first=()=>Thread.Sleep(x);}
        first();return 0;}}""")
    assert result["total_ms"] == 2


def test_foreach_item_type_resolves_overloads_and_shadows_a_same_named_member():
    result = analyze("""class Demo {string x;void Pause(int value){Thread.Sleep(value);}
        void Pause(string value){Thread.Sleep(999);}
        public int DoWork(){foreach(var x in new int[]{2,3}){Pause(x);}return 0;}}""")
    assert result["total_ms"] == 5


@pytest.mark.parametrize("items", ["2", "2,3"])
def test_known_list_modification_invalidates_its_enumerator(items):
    result = analyze(
        "using System.Collections.Generic;class Demo {public int DoWork(){"
        f"var a=new List<int>{{{items}}};foreach(var x in a){{Thread.Sleep(x);a.Add(7);}}"
        "Thread.Sleep(999);return 0;}}"
    )
    assert result["execution_status"] == "unavailable"
    assert result["total_ms"] is None
    assert not any(s.get("milliseconds") == 999 for s in result["stages"])


def test_unknown_collection_does_not_become_a_single_iteration_or_an_empty_list():
    result = analyze("""class Demo {IEnumerable<int> values;
        public int DoWork(){foreach(var x in values){Thread.Sleep(3);}return 0;}}""")
    assert result["known_delay_min_ms"] == 0
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("int i=0;int[] a=new[]{2,3};a[i++]+=5;Thread.Sleep(a[0]+i);", 8),
        ("int i=0;int[] a=new[]{2,3};Thread.Sleep(a[i++]++);Thread.Sleep(a[0]+i);", 6),
        ("int i=0;int[] a=new[]{2,3};Thread.Sleep(a[i++]+i);", 3),
        ("int x=2;var a=new[]{x,++x};foreach(var v in a){Thread.Sleep(v);}", 5),
        ("int x=2;var a=new List<int>{x,++x};foreach(var v in a){Thread.Sleep(v);}", 5),
        ("int[] a=new[]{2};Change(ref a[0]);Thread.Sleep(a[0]);", 7),
        ("int i=2;int[] a=new[]{3};Thread.Sleep(i+a[0]++);Thread.Sleep(a[0]);", 9),
        ("int i=2;int[] a=new[]{3};Thread.Sleep(i+(i=7));", 9),
    ],
)
def test_collection_elements_freeze_evaluation_order_and_share_ref_storage(body, expected):
    result = analyze(
        "using System.Collections.Generic;class Demo {void Change(ref int x){x=7;}"
        f"public int DoWork(){{{body}return 0;}}}}"
    )
    assert result["total_ms"] == expected


def test_element_assignment_evaluates_receiver_and_subscript_before_the_rhs():
    result = analyze("""class Demo {int[] a;int[] original;
        int[] Get(){Thread.Sleep(2);return a;}
        int Position(){Thread.Sleep(3);return 0;}
        int Change(){Thread.Sleep(5);a=new[]{99};return 7;}
        public int DoWork(){a=new[]{2};original=a;Get()[Position()]=Change();
        Thread.Sleep(original[0]);Thread.Sleep(a[0]);return 0;}}""")
    assert result["total_ms"] == 116


@pytest.mark.parametrize("call", ["api.Update(a)", "api.Read(ref a[0])"])
def test_unknown_external_collection_write_does_not_reuse_previous_element_values(call):
    result = analyze(
        "class Demo {External api;public int DoWork(){int[] a=new[]{2,3};"
        f"{call};foreach(var x in a){{Thread.Sleep(x);}}return 0;}}}}"
    )
    assert result["total_ms"] is None and result["known_delay_max_ms"] is None


def test_list_call_keeps_the_receiver_evaluated_before_its_argument_changes_the_field():
    result = analyze("""using System.Collections.Generic;class Demo {List<int> a;
        int Change(){a=new List<int>{99};return 7;}
        public int DoWork(){a=new List<int>{2};var original=a;a.Add(Change());
        foreach(var x in original){Thread.Sleep(x);}Thread.Sleep(a.Count);return 0;}}""")
    assert result["total_ms"] == 10


def test_background_external_write_invalidates_array_contents_without_a_known_item_slot():
    result = analyze("""class Demo {External api;public int DoWork(){var a=new[]{2,3};
        Task.Run(()=>api.Update(a));foreach(var x in a){Thread.Sleep(x);}return 0;}}""")
    assert result["total_ms"] is None and result["known_delay_max_ms"] is None


def test_large_list_copy_does_not_treat_uncopied_numeric_items_as_zero():
    result = analyze("""using System.Collections.Generic;using System.Linq;
        class Demo {public int DoWork(){var a=new List<int>(Enumerable.Range(2,5000));
        Thread.Sleep(a[0]);return 0;}}""")
    assert result["total_ms"] is None and result["known_delay_max_ms"] is None


def test_normal_object_constructor_return_does_not_become_a_null_collection_result():
    result = analyze("""class Settings {public int Delay;public Settings(){Delay=7;return;}}
        class Demo {public int DoWork(){var settings=new Settings();
        Thread.Sleep(settings.Delay);return 0;}}""")
    assert result["total_ms"] == 7
