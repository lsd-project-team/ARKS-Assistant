"""目录与执行使用相同词法类型；多维数组按真实维度和元素数计算。"""

import hashlib

import pytest

from app.modules.action_timing.source_index import SourceIndex, text, walk
from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.workspace import Workspace
from tests.unit.test_source_timing_dependencies import analyze


def test_foreach_var_call_is_visible_to_the_catalog_before_execution(tmp_path):
    (tmp_path / "Demo.cs").write_text(
        "using System.Collections.Generic;class Item {public void Pause(){Thread.Sleep(7);}}"
        "class Demo {List<Item> items;void Scan(){foreach(var item in items){item.Pause();}}"
        "public void Start(){Scan();}}",
        encoding="utf-8",
    )
    rows = SourceTiming(Workspace(tmp_path)).summary()["rows"]
    assert {"Pause", "Scan", "Start"} <= {row["method"] for row in rows}
    scan = next(row for row in rows if row["method"] == "Scan")
    assert scan["known_delay_max_ms"] is None


def test_each_foreach_keeps_its_lexical_type_and_does_not_shadow_an_outside_field():
    source = """using System.Collections.Generic;
        class First {public void Pause(){Thread.Sleep(2);}}
        class Second {public void Pause(){Thread.Sleep(3);}}
        class Last {public void Pause(){Thread.Sleep(5);}}
        class Demo {Last item;List<First> first;List<Second> second;
        public int DoWork(){foreach(var item in first){item.Pause();}
        foreach(var item in second){item.Pause();}item.Pause();return 0;}}"""
    index = SourceIndex(
        [
            {
                "path": "Demo.cs",
                "content": source,
                "version": hashlib.sha256(source.encode()).hexdigest(),
            }
        ]
    )
    method = index.by_method[("Demo", "DoWork")][0]
    calls = [
        node
        for node in walk(method.body)
        if node.type == "invocation_expression" and text(node) == "item.Pause()"
    ]
    assert [
        index.resolve(node, method).owner if index.resolve(node, method) else None for node in calls
    ] == ["First", "Second", "Last"]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("foreach(int x in new int[,]{{2,3},{5,7}}){Thread.Sleep(x);}", 17),
        ("foreach(int x in new int[,]{{2,3},{5,7}}){Thread.Sleep(5);}", 20),
        ("foreach(var x in new[,]{{2,3},{5,7}}){Thread.Sleep(x);}", 17),
        ("foreach(int x in new int[2,3]){Thread.Sleep(x+2);}", 12),
        ("foreach(int x in new int[2,0]){Thread.Sleep(999);}Thread.Sleep(7);", 7),
        ("var a=new int[,]{{2,3},{5,7}};a[1,0]=11;Thread.Sleep(a[1,0]);", 11),
        ("var a=new int[2,3];a[1,2]=7;Change(ref a[1,2]);Thread.Sleep(a[1,2]);", 13),
        ("var a=new int[,]{{2,3},{5,7}};foreach(var x in a){Thread.Sleep(x);if(x==5)break;}", 10),
        ("var a=new int[1,2,2];a[0,1,1]=9;Thread.Sleep(a.Length+a[0,1,1]);", 13),
        ("var a=new int[][]{new[]{2,3},new[]{5}};Thread.Sleep(a[0][1]+a[1][0]);", 8),
        ("var a=new List<int>();a.Add(7);Thread.Sleep(a[0]);", 7),
        (
            "var a=new int[,]{{2,3},{5,7}};int last=0;foreach(var x in a){last=x;}"
            "Thread.Sleep(last);",
            7,
        ),
        (
            "var a=new int[2,3];"
            "Thread.Sleep(a.Rank+a.GetLength(0)+a.GetLength(1)+a.GetUpperBound(1));",
            9,
        ),
    ],
)
def test_rectangular_array_shape_values_and_shared_element_state(body, expected):
    result = analyze(
        "using System.Collections.Generic;"
        f"class Demo {{void Change(ref int x){{x=13;}}public int DoWork(){{{body}return 0;}}}}"
    )
    assert result["total_ms"] == expected


def test_dimension_expressions_preserve_their_own_values_before_later_side_effects():
    result = analyze("""class Demo {public int DoWork(){int n=2;
        var a=new int[n,n++];Thread.Sleep(a.Length);return 0;}}""")
    assert result["total_ms"] == 4


def test_element_indices_preserve_receiver_and_left_to_right_side_effects():
    result = analyze("""class Demo {int index;
        int First(){Thread.Sleep(2);return index++;}int Second(){Thread.Sleep(3);return index++;}
        public int DoWork(){index=0;var a=new int[2,2];
        a[First(),Second()]=7;Thread.Sleep(a[0,1]);return 0;}}""")
    assert result["total_ms"] == 12


def test_jagged_outer_array_counts_inner_arrays_instead_of_rectangular_elements():
    result = analyze("""class Demo {public int DoWork(){
        foreach(var part in new int[][]{new[]{2,3},new[]{5}}){
            foreach(var x in part){Thread.Sleep(x);}}return 0;}}""")
    assert result["total_ms"] == 10


def test_implicit_rectangular_element_and_shape_query_types_resolve_overloads():
    result = analyze("""class Demo {void Pause(int x){Thread.Sleep(x);}
        void Pause(string x){Thread.Sleep(999);}
        public int DoWork(){var a=new[,]{{2,3},{5,7}};
        foreach(var x in a){Pause(x);}Pause(a.GetLength(0));Pause(a.Length);return 0;}}""")
    assert result["total_ms"] == 23


def test_dimension_using_an_element_access_preserves_the_array_element_type():
    result = analyze("""class Demo {void Pause(int x){Thread.Sleep(x);}
        void Pause(string x){Thread.Sleep(999);}public int DoWork(){
        var sizes=new[]{2,3};var a=new int[sizes[0],sizes[1]];
        foreach(var x in a){Pause(x+1);}return 0;}}""")
    assert result["total_ms"] == 6


def test_mixed_numeric_implicit_array_uses_the_common_element_type():
    result = analyze("""class Demo {void Pause(double x){Thread.Sleep(x);}
        void Pause(int x){Thread.Sleep(999);}public int DoWork(){
        foreach(var x in new[,]{{2,3.0},{5,7}}){Pause(x);}return 0;}}""")
    assert result["total_ms"] == 17


def test_small_integer_arithmetic_promotes_to_int_for_overload_binding():
    result = analyze("""class Demo {void Pause(int x){Thread.Sleep(x);}
        void Pause(byte x){Thread.Sleep(999);}public int DoWork(){
        foreach(var x in new byte[,]{{2,3}}){Pause(x+(byte)1);}return 0;}}""")
    assert result["total_ms"] == 7


@pytest.mark.parametrize(
    "body",
    [
        "var a=new double[,]{{3}};Thread.Sleep(a[0,0]/2);",
        "var a=new double[1,1];a[0,0]=3;Thread.Sleep(a[0,0]/2);",
        "var a=new[]{3,4.0};Thread.Sleep(a[0]/2);",
        "delay=3;Thread.Sleep(delay/2);",
        "Thread.Sleep(Three()/2);",
    ],
)
def test_numeric_element_conversion_preserves_floating_division(body):
    result = analyze(
        f"class Demo {{double delay;double Three()=>3;public int DoWork(){{{body}return 0;}}}}"
    )
    assert result["total_ms"] == 1.5


def test_literal_suffixes_and_hex_digits_keep_their_types_and_values():
    result = analyze("""class Demo {void Pause(long x){Thread.Sleep(2);}
        void Pause(int x){Thread.Sleep(999);}public int DoWork(){
        foreach(var x in new[]{2L,3L}){Pause(x);}Thread.Sleep(0xF);return 0;}}""")
    assert result["total_ms"] == 19
