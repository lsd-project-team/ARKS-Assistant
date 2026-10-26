"""额度不足后仍核对源码组成；不把条件、未执行回调或可变量当固定总值。"""

import pytest

from app.modules.action_timing import source_budget
from tests.unit.test_source_timing_audit_gaps import report


def boundary_report(tmp_path, monkeypatch, helpers, body):
    monkeypatch.setattr(source_budget, "MAX_CALL_DEPTH", 1)
    rows = report(tmp_path, "using System;class Demo{" + helpers + "void Start(){" + body + "}}")[
        "rows"
    ]
    return next(r for r in rows if r["method"] == "Start")


def parts(row):
    return [s for s in row["source_components"] if "继续核对" in s["note"]]


def test_continuation_follows_arbitrary_depth_and_literal_arguments(tmp_path, monkeypatch):
    row = boundary_report(
        tmp_path,
        monkeypatch,
        "void A(int delay){B(delay+2);}void B(int delay){C(delay);}"
        "void C(int delay){for(int n=0;n<3;n++)Thread.Sleep(delay);}",
        "A(5);",
    )
    assert row["truncated"] and row["total_ms"] is None
    assert any(p["milliseconds"] == 21 for p in parts(row))
    assert row["continuation_audit"]["pending_contexts"] == 0
    assert any("delay=7" in c for p in parts(row) for c in p["conditions"])


def test_continuation_uses_named_and_optional_arguments_and_known_loop_count(tmp_path, monkeypatch):
    row = boundary_report(
        tmp_path,
        monkeypatch,
        "void A(){B(count:5);}void B(int delay=11,int count=1){"
        "for(int n=0;n<count;n++)Thread.Sleep(delay);}",
        "A();",
    )
    assert any(p["milliseconds"] == 55 and not p["factors"] for p in parts(row))


@pytest.mark.parametrize(
    "mutation",
    ["delay++;", "++delay;", "delay=99;", "Change(ref delay);", "Action saved=()=>{delay++;};"],
)
def test_continuation_does_not_reuse_a_written_parameter(tmp_path, monkeypatch, mutation):
    row = boundary_report(
        tmp_path,
        monkeypatch,
        "void A(int delay){" + mutation + "Thread.Sleep(delay);}void Change(ref int n){n=99;}",
        "A(5);",
    )
    assert not parts(row)


@pytest.mark.parametrize(
    "body",
    [
        "if(false)Hidden();",
        "while(false){Hidden();}",
        "return;Hidden();",
        "for(int n=0;n<0;n++)Hidden();",
        "Action saved=()=>Hidden();",
    ],
)
def test_continuation_does_not_follow_unreachable_or_saved_code(tmp_path, monkeypatch, body):
    row = boundary_report(
        tmp_path,
        monkeypatch,
        "void A(){" + body + "}void Hidden(){Thread.Sleep(999);}",
        "A();Thread.Sleep(1);",
    )
    assert not any(p["milliseconds"] == 999 for p in parts(row))


def test_continuation_respects_proven_parameter_guard(tmp_path, monkeypatch):
    row = boundary_report(
        tmp_path,
        monkeypatch,
        "void A(int n){if(n<0)Hidden();else Thread.Sleep(7);}void Hidden(){Thread.Sleep(999);}",
        "A(5);",
    )
    assert any(p["milliseconds"] == 7 for p in parts(row))
    assert not any(p["milliseconds"] == 999 for p in parts(row))


def test_continuation_traces_task_method_calls_as_conditional_background(tmp_path, monkeypatch):
    row = boundary_report(
        tmp_path, monkeypatch, "void A(){Task.Run(()=>B());}void B(){Thread.Sleep(37);}", "A();"
    )
    assert any(p["milliseconds"] == 37 and p["deferred"] for p in parts(row))
    assert row["total_ms"] is None


def test_continuation_marks_recursive_call_without_inventing_iterations(tmp_path, monkeypatch):
    row = boundary_report(tmp_path, monkeypatch, "void A(int n){Thread.Sleep(n);A(n+1);}", "A(5);")
    assert row["continuation_audit"]["recursive_targets"]
    assert row["continuation_audit"]["pending_contexts"] == 0
    assert row["total_ms"] is None
    assert any(p["milliseconds"] == 5 for p in parts(row))


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ("int delay=3+4;", {7}),
        ("const int delay=17;", {17}),
        ("int delay=Ready()?11:23;", {11, 23}),
        ("int delay=Mode() switch{1=>31,2=>43,_=>59};", {31, 43, 59}),
        ("int delay=2 switch{1=>31,2=>43,_=>59};", {43}),
    ],
)
def test_continuation_retains_pure_local_and_branch_values(
    tmp_path, monkeypatch, declaration, expected
):
    row = boundary_report(
        tmp_path,
        monkeypatch,
        "extern bool Ready();extern int Mode();void A(){" + declaration + "Thread.Sleep(delay);}",
        "A();",
    )
    assert {p["milliseconds"] for p in parts(row)} == expected
    assert row["total_ms"] is None


def test_continuation_does_not_use_mutable_field_defaults(tmp_path, monkeypatch):
    row = boundary_report(
        tmp_path, monkeypatch, "int delay=57;void A(){Thread.Sleep(delay);}", "A();"
    )
    assert not parts(row)


def test_constant_uses_declaration_scope_instead_of_callers_parameter(tmp_path, monkeypatch):
    monkeypatch.setattr(source_budget, "MAX_CALL_DEPTH", 1)
    result = report(
        tmp_path,
        "class Constants{const int baseDelay=3;public const int Delay=baseDelay+4;}"
        "class Demo{void Start(){A(999);}void A(int baseDelay){Thread.Sleep(Constants.Delay);}}",
    )
    row = next(r for r in result["rows"] if r["method"] == "Start")
    assert any(p["milliseconds"] == 7 for p in parts(row))
    assert not any(p["milliseconds"] == 1003 for p in parts(row))


def test_continuation_traces_constructor_base_and_setter(tmp_path, monkeypatch):
    monkeypatch.setattr(source_budget, "MAX_CALL_DEPTH", 1)
    result = report(
        tmp_path,
        "class Base{public Base(){Thread.Sleep(3);}}class Child:Base{}"
        "class Demo{int Delay{set{Thread.Sleep(value);}}"
        "void Start(){A();}void A(){new Child();Delay=7;}}",
    )
    row = next(r for r in result["rows"] if r["method"] == "Start")
    assert {p["milliseconds"] for p in parts(row)} >= {3, 7}


def test_projection_boundary_is_explicit(tmp_path, monkeypatch):
    from app.modules.action_timing import source_continuations

    monkeypatch.setattr(source_continuations, "MAX_CONTEXTS", 1)
    row = boundary_report(tmp_path, monkeypatch, "void A(){B();}void B(){Thread.Sleep(3);}", "A();")
    assert row["continuation_audit"]["pending_contexts"] > 0
    assert any(
        "补充源码核对仍有" in text for r in row["missing_requirements"] for text in r["required"]
    )


@pytest.mark.parametrize(
    ("declaration", "expected"), [("int delay=5;", {5}), ("int delay=Read();", set())]
)
def test_local_shadows_same_named_class_constant(tmp_path, monkeypatch, declaration, expected):
    row = boundary_report(
        tmp_path,
        monkeypatch,
        "const int delay=77;extern int Read();void A(){" + declaration + "Thread.Sleep(delay);}",
        "A();",
    )
    assert {p["milliseconds"] for p in parts(row)} == expected


def test_source_local_constant_loop_count_is_solved(tmp_path, monkeypatch):
    row = boundary_report(
        tmp_path,
        monkeypatch,
        "void A(){int count=5;for(int n=0;n<count;n++)Thread.Sleep(7);}",
        "A();",
    )
    assert any(p["milliseconds"] == 35 and not p["factors"] for p in parts(row))


def test_numeric_expression_protection_is_not_reported_as_missing_parameters(tmp_path, monkeypatch):
    from app.modules.action_timing import source_component_values

    monkeypatch.setattr(source_component_values, "MAX_VARIANTS", 1)
    row = boundary_report(
        tmp_path,
        monkeypatch,
        "extern bool Ready();void A(){int delay=(Ready()?1:2)+(Ready()?3:4);Thread.Sleep(delay);}",
        "A();",
    )
    assert row["continuation_audit"]["pending_contexts"] > 0
    assert any("补充源码核对仍有" in s for r in row["missing_requirements"] for s in r["required"])


@pytest.mark.parametrize("creation", ["new Item{Delay=7};", "new Container{Item={Delay=7}};"])
def test_initializer_setter_belongs_to_created_object(tmp_path, monkeypatch, creation):
    monkeypatch.setattr(source_budget, "MAX_CALL_DEPTH", 1)
    result = report(
        tmp_path,
        "class Item{public int Delay{set{Thread.Sleep(value);}}}"
        "class Container{public Item Item{get;set;}=new Item();}"
        "class Demo{int Delay{set{Thread.Sleep(999);}}"
        "void Start(){A();}void A(){" + creation + "}}",
    )
    row = next(r for r in result["rows"] if r["method"] == "Start")
    assert any(p["milliseconds"] == 7 for p in parts(row))
    assert not any(p["milliseconds"] == 999 for p in parts(row))
