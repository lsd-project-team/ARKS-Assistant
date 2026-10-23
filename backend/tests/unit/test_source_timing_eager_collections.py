"""即时集合操作须先执行筛选，再按结果执行回调；不提前执行惰性查询。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


def listing(body, declarations=""):
    return analyze(
        "using System;using System.Collections.Generic;using System.Linq;"
        + declarations
        + "class Demo {public int DoWork(){"
        + body
        + "return 0;}}"
    )


@pytest.mark.parametrize(
    "body,expected",
    [
        ("new List<int>{1,2,3}.FindAll(n=>n>1).ForEach(n=>Thread.Sleep(n));", 5),
        (
            "new List<int>{1,2,3}.FindAll(n=>{Thread.Sleep(2);return n>1;})"
            ".ForEach(n=>Thread.Sleep(n));",
            11,
        ),
        ("new List<int>{2,3}.FindAll(n=>false).ForEach(n=>Thread.Sleep(999));Thread.Sleep(2);", 2),
        (
            "new List<int>().FindAll(n=>{Thread.Sleep(999);return true;})"
            ".ForEach(n=>Thread.Sleep(999));Thread.Sleep(2);",
            2,
        ),
        (
            "int delay=1;new List<int>{2,3,4}.FindAll(n=>{Thread.Sleep(delay++);return n>2;})"
            ".ForEach(n=>Thread.Sleep(n));Thread.Sleep(delay);",
            17,
        ),
        ("new[]{3,7}.ToList().ForEach(n=>Thread.Sleep(n));", 10),
        (
            "var source=new List<int>{2,3};var copy=source.ToList();source[0]=99;"
            "copy.ForEach(n=>Thread.Sleep(n));",
            5,
        ),
        ("Enumerable.Range(2,3).ToList().ForEach(n=>Thread.Sleep(n));", 9),
        ("System.Linq.Enumerable.ToList(new[]{3,7}).ForEach(n=>Thread.Sleep(n));", 10),
        (
            "var source=new List<int>{2,3};var copy=source.FindAll(n=>true);copy.Add(7);"
            "source.ForEach(n=>Thread.Sleep(n));copy.ForEach(n=>Thread.Sleep(n));",
            17,
        ),
        (
            "var source=new List<int>{2,3};source.FindAll(n=>{source=new List<int>{99};"
            "return true;}).ForEach(n=>Thread.Sleep(n));",
            5,
        ),
        ("var query=new[]{2,3}.Select(n=>{Thread.Sleep(999);return n;});Thread.Sleep(2);", 2),
        ("new List<int>{2,3}.FindAll(match:n=>n>2).ForEach(n=>Thread.Sleep(n));", 3),
    ],
)
def test_eager_collection_results_preserve_order_values_and_copy_identity(body, expected):
    assert listing(body)["total_ms"] == expected


def test_to_list_copies_references_so_later_object_writes_remain_visible():
    result = listing(
        "var item=new Item{delay=3};var copy=new List<Item>{item}.ToList();"
        "item.delay=7;copy.ForEach(n=>Thread.Sleep(n.delay));",
        "class Item{public int delay;}",
    )
    assert result["total_ms"] == 7


def test_source_owned_to_list_is_not_replaced_by_a_framework_contract():
    result = listing(
        "new Values().ToList().ForEach(n=>Thread.Sleep(n));",
        "class Values{public List<int> ToList(){Thread.Sleep(11);return new List<int>{3};}}",
    )
    assert result["total_ms"] == 14


def test_find_all_reloads_the_item_after_the_predicate_instead_of_using_its_old_argument():
    result = listing(
        "var items=new List<int>{2,3};items.FindAll(n=>{items[0]=7;return true;})"
        ".ForEach(n=>Thread.Sleep(n));"
    )
    assert result["total_ms"] == 10


def test_unknown_input_count_does_not_keep_one_predicate_samples_captured_write():
    result = listing(
        "int delay=3;List<int> items=ReadList();"
        "items.FindAll(n=>{delay++;return true;});Thread.Sleep(delay);"
    )
    assert result["total_ms"] is None
    assert result["known_delay_min_ms"] == 0


def test_unknown_predicate_keeps_the_preceding_delay_and_does_not_select_all_items():
    result = listing(
        "bool keep=ReadFlag();Thread.Sleep(11);new List<int>{3,7}"
        ".FindAll(n=>keep).ForEach(n=>Thread.Sleep(n));"
    )
    assert result["known_delay_min_ms"] == 11 and result["total_ms"] is None


def test_find_all_method_group_and_predicate_delegate_keep_the_returned_bool():
    result = analyze("""using System;using System.Collections.Generic;
        class Demo {bool Keep(int n){Thread.Sleep(2);return n>1;}public int DoWork(){
        Predicate<int> predicate=Keep;new List<int>{1,2,3}.FindAll(predicate)
        .ForEach(n=>Thread.Sleep(n));return 0;}}""")
    assert result["total_ms"] == 11


def test_empty_collection_still_validates_the_find_all_callback():
    result = listing("Predicate<int> predicate=null;new List<int>().FindAll(predicate);")
    assert result["total_ms"] is None


@pytest.mark.parametrize("operation", ["FindAll", "ForEach"])
def test_unknown_collection_callback_invalidates_the_old_member_delay(operation):
    kind = "Predicate<int>" if operation == "FindAll" else "Action<int>"
    result = analyze(
        "using System;using System.Collections.Generic;class Demo{int delay=7;"
        + kind
        + " callback;public int DoWork(){new List<int>{1}."
        + operation
        + "(callback);Thread.Sleep(delay);return 0;}}"
    )
    assert result["known_delay_min_ms"] == 0 and result["total_ms"] is None


def test_an_unknown_enumerator_cannot_leave_its_old_receiver_state_as_fixed_delay():
    result = analyze("""using System.Collections.Generic;using System.Linq;
        class Demo{IEnumerable<int> items;int delay=7;public int DoWork(){
        items.ToList();Thread.Sleep(delay);return 0;}}""")
    assert result["known_delay_min_ms"] == 0 and result["total_ms"] is None


def test_copying_a_framework_list_of_unknown_size_does_not_rewrite_other_fields():
    result = analyze("""using System.Collections.Generic;using System.Linq;
        class Demo{List<int> items;int delay=7;public int DoWork(){
        items.ToList();Thread.Sleep(delay);return 0;}}""")
    assert result["known_delay_min_ms"] == 7 and result["total_ms"] is None


def test_unknown_enumerator_does_not_erase_an_unrelated_callers_private_parameters():
    result = listing(
        "var parameter=new Parameter{Delay=20};new Data().Read();Thread.Sleep(parameter.Delay);",
        "class Parameter{public int Delay;}"
        "class Data{IEnumerable<int> items;int delay=7;public void Read(){"
        "items.ToList();Thread.Sleep(delay);}}",
    )
    assert result["known_delay_min_ms"] == 20 and result["total_ms"] is None


def control_listing(body, *, verified=True, base="XtraUserControl", owned=""):
    from app.modules.action_timing.source_collection_types import (
        INFRASTRUCTURE,
        INFRASTRUCTURE_SHA256,
    )
    from app.modules.action_timing.source_estimator import Estimator
    from app.modules.action_timing.source_index import SourceIndex

    code = (
        "using System;using System.Collections.Generic;using DevExpress.XtraEditors;"
        "using AKRS.Galaxy2.Infrastructure.ControlServices;class Child:XtraUserControl{}"
        f"class Demo:{base}{{" + owned + "public int DoWork(){" + body + "return 0;}}"
    )
    index = SourceIndex([{"path": "main.cs", "content": code, "version": "fixture"}])
    index.packages = {
        INFRASTRUCTURE: {
            "verified": verified,
            "sha256": INFRASTRUCTURE_SHA256 if verified else "changed",
        }
    }
    return Estimator(index).estimate(index.by_method[("Demo", "DoWork")][0])


def test_verified_external_control_list_enables_the_per_item_callback_without_guessing_count():
    result = control_listing("this.GetChildControls<Child>().ForEach(c=>Thread.Sleep(7));")
    assert result["total_ms"] is None and result["known_delay_min_ms"] == 0
    assert result["per_item_timing"] == [{"element_type": "Child", "min_ms": 7, "max_ms": 7}]


@pytest.mark.parametrize("changes", [{"verified": False}, {"base": "object"}])
def test_external_control_list_contract_requires_the_artifact_and_receiver_type(changes):
    result = control_listing(
        "this.GetChildControls<Child>().ForEach(c=>Thread.Sleep(7));", **changes
    )
    assert "per_item_timing" not in result
    assert not any(s["kind"] == "delay" and s["milliseconds"] == 7 for s in result["stages"])


def test_source_owned_control_query_retains_its_body_instead_of_the_package_contract():
    result = control_listing(
        "this.GetChildControls().ForEach(c=>Thread.Sleep(7));",
        owned="List<Child> GetChildControls(){Thread.Sleep(13);"
        "return new List<Child>{new Child()};}",
    )
    assert result["total_ms"] == 20


def test_control_query_type_evidence_does_not_claim_the_receivers_old_fields_are_unchanged():
    result = control_listing(
        "this.GetChildControls<Child>();Thread.Sleep(delay);", owned="int delay=7;"
    )
    assert result["known_delay_min_ms"] == 0 and result["total_ms"] is None


def test_source_owned_range_return_type_is_preserved_through_to_list():
    result = listing(
        "Enumerable.Range().ToList().ForEach(n=>Thread.Sleep(n.delay));",
        "class Item{public int delay=7;}"
        "class Enumerable{public static List<Item> Range(){return new List<Item>{new Item()};}}",
    )
    assert result["total_ms"] == 7


@pytest.mark.parametrize("expression", ["new Data().Items", "new Data().Read()"])
def test_collection_type_uses_the_declaration_file_namespace(expression):
    result = analyze(
        "class Demo{public int DoWork(){"
        + expression
        + ".FindAll(n=>n>1).ForEach(n=>Thread.Sleep(n));return 0;}}",
        "using System.Collections.Generic;class Data{"
        "public List<int> Items=new List<int>{2,3};public List<int> Read(){return Items;}}",
    )
    assert result["total_ms"] == 5


def test_field_list_initializer_value_is_saved_after_its_side_effect_runs_once():
    result = listing(
        "new Data().Items.ForEach(n=>Thread.Sleep(n));",
        "class Data{public List<int> Items=Make();static List<int> Make(){"
        "Thread.Sleep(3);return new List<int>{2,3};}}",
    )
    assert result["total_ms"] == 8


def test_constructor_updates_the_same_field_list_that_later_callbacks_read():
    result = listing(
        "new Data().Items.ForEach(n=>Thread.Sleep(n));",
        "class Data{public List<int> Items=new List<int>{2};public Data(){Items.Add(3);}}",
    )
    assert result["total_ms"] == 5


def test_separate_instances_have_separate_initialized_field_lists():
    result = listing(
        "var one=new Data();var two=new Data();one.Items.Add(7);"
        "one.Items.ForEach(n=>Thread.Sleep(n));two.Items.ForEach(n=>Thread.Sleep(n));",
        "class Data{public List<int> Items=new List<int>{2};}",
    )
    assert result["total_ms"] == 11


def test_unknown_initialization_does_not_make_the_old_field_list_a_guaranteed_lower_bound():
    result = listing(
        "new Data().Items.ForEach(n=>Thread.Sleep(n));",
        "class Data:ExternalBase{public List<int> Items=new List<int>{2};"
        "public Data(){InitializeComponent();}}",
    )
    assert result["known_delay_min_ms"] == 0 and result["total_ms"] is None
