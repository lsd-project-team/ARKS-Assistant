"""构造不是无耗时语句：参数、字段、this/base 链以及后台委托各自有边界。"""

import pytest

from app.modules.action_timing.source_estimator import Estimator
from app.modules.action_timing.source_index import SourceIndex
from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.workspace import Workspace
from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(("creation", "expected"), [("new Worker(7)", 10), ("new Worker()", 14)])
def test_constructor_arguments_and_optional_source_default(creation, expected):
    result = analyze(f"""class Demo {{ public int DoWork() {{
        {creation}; Thread.Sleep(3); return 0; }} }}
        class Worker {{ public Worker(int ms=11) {{ Thread.Sleep(ms); }} }}""")
    assert result["total_ms"] == expected


def test_this_base_and_instance_fields_execute_once_per_object():
    result = analyze("""class Base { int x=Init(2); protected Base(int ms) { Thread.Sleep(ms); }
        int Init(int ms) { Thread.Sleep(ms); return ms; } }
        class Worker : Base { int y=Init(3); public Worker():this(4) { Thread.Sleep(5); }
        public Worker(int ms):base(ms) { Thread.Sleep(6); }
        int Init(int ms) { Thread.Sleep(ms); return ms; } }
        class Demo { public int DoWork() { new Worker(); return 0; } }""")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 20
    assert result["total_ms"] == 20


def test_implicit_constructor_includes_fields_and_base_but_not_static_fields():
    result = analyze("""class Base { public Base() { Thread.Sleep(2); } }
        class Worker:Base { int x=Init(3); static int y=Init(100);
        static int Init(int ms) { Thread.Sleep(ms); return ms; } }
        class Demo { public int DoWork() { new Worker(); new Worker(); return 0; } }""")
    assert result["total_ms"] == 10
    assert not any(stage.get("milliseconds") == 100 for stage in result["stages"])


def test_constructor_argument_side_effects_are_evaluated_before_ctor_body():
    result = analyze("""class Worker { public Worker(int ms) { Thread.Sleep(ms); } }
        class Demo { int Delay() { Thread.Sleep(2); return 7; }
        public int DoWork() { new Worker(Delay()); return 0; } }""")
    assert result["total_ms"] == 9


def test_ambiguous_constructor_is_unknown_and_arrow_body_is_not_skipped():
    ambiguous = analyze("""class Worker { public Worker(int v) { Thread.Sleep(10); }
        public Worker(double v) { Thread.Sleep(90); } }
        class Demo { public int DoWork() { new Worker(unknown); return 0; } }""")
    assert ambiguous["total_ms"] is None
    assert not any(stage["kind"] == "delay" for stage in ambiguous["stages"])
    arrow = analyze("""class Demo { void Slow()=>Thread.Sleep(7);
        public int DoWork() { Slow(); Thread.Sleep(3); return 0; } }""")
    assert arrow["total_ms"] == 10


def test_collection_remove_is_not_motion_but_custom_source_remove_is_expanded():
    collection = analyze("""class Demo { List<int> values; public int DoWork() {
        values.RemoveAt(0); Thread.Sleep(7); return 0; } }""")
    assert collection["total_ms"] == 7 and collection["motion_count"] == 0
    custom = analyze("""class Machine { public void RemoveAt(int index) { Thread.Sleep(5); } }
        class Demo { Machine machine; public int DoWork() { machine.RemoveAt(0);
        Thread.Sleep(7); return 0; } }""")
    assert custom["total_ms"] == 12 and custom["motion_count"] == 0


def test_standalone_constructor_can_use_optional_defaults():
    index = SourceIndex(
        [
            {
                "path": "Worker.cs",
                "version": "fixture",
                "content": "class Worker { public Worker(int ms=11) { Thread.Sleep(ms); } }",
            }
        ]
    )
    result = Estimator(index).estimate(index.by_method[("Worker", ".ctor")][0])
    assert result["total_ms"] == 11


def test_catalog_includes_motion_constructors_and_manual_output_buttons(tmp_path):
    path = tmp_path / "CalibSystem/Controls/Teach.cs"
    path.parent.mkdir(parents=True)
    path.write_text(
        """class Teach { Axis axis; public Teach() { axis.AbsoluteMove(10); } }
        class Manual { Electric output; void Click() { output.SetOutputValue(true); }
        void TeachClick() { new Teach(); } }""",
        encoding="utf-8",
    )
    rows = SourceTiming(Workspace(tmp_path)).summary()["rows"]
    assert {("Teach", ".ctor"), ("Manual", "Click"), ("Manual", "TeachClick")} <= {
        (row["class_name"], row["method"]) for row in rows
    }
    ctor = next(row for row in rows if row["class_name"] == "Teach")
    assert ctor["motion_count"] == 1 and ctor["total_ms"] is None
