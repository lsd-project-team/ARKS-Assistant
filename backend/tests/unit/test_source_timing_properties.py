"""属性读取/写入不能丢掉动作，也不能把名字、委托定义当作执行。"""

from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.workspace import Workspace
from tests.unit.test_source_timing_dependencies import analyze


def test_getter_delay_and_return_value_are_both_used_once():
    result = analyze("""class Settings { public int Delay { get { Thread.Sleep(3); return 7; } } }
        class Demo { Settings settings; public int DoWork() {
        Thread.Sleep(settings.Delay); return 0; } }""")
    assert result["total_ms"] == 10
    assert [stage["milliseconds"] for stage in result["stages"] if stage["kind"] == "delay"] == [
        3,
        7,
    ]


def test_setter_and_compound_get_then_set_receive_correct_value():
    direct = analyze("""class Motor { public int Position { set { Thread.Sleep(value); } } }
        class Demo { Motor motor; public int DoWork() { motor.Position=7; return 0; } }""")
    assert direct["total_ms"] == 7
    compound = analyze("""class Motor { public int Position {
        get { Thread.Sleep(3); return 5; } set { Thread.Sleep(value); } } }
        class Demo { Motor motor; public int DoWork() { motor.Position+=2; return 0; } }""")
    assert compound["total_ms"] == 10


def test_rhs_is_read_before_assignment_and_object_initializer_runs_after_ctor():
    assigned = analyze("""class Motor { public int Position { get { return 5; }
        set { Thread.Sleep(value); } } }
        class Demo { Motor motor; public int DoWork() { motor.Position=motor.Position+2;
        return 0; } }""")
    assert assigned["total_ms"] == 7
    initialized = analyze("""class Motor { public Motor() { Thread.Sleep(3); }
        public int Position { set { Thread.Sleep(value); } } }
        class Demo { public int DoWork() { new Motor { Position=7 }; return 0; } }""")
    assert initialized["total_ms"] == 10


def test_arrow_property_and_numeric_parameter_conversion_keep_csharp_semantics():
    result = analyze("""class Demo { int Delay=>MakeDelay(); int MakeDelay()=>7;
        void Pause(double value)=>Thread.Sleep((int)(value/2*10));
        public int DoWork() { Pause(5); Thread.Sleep(Delay); return 0; } }""")
    assert result["total_ms"] == 32


def test_nameof_and_uninvoked_delegate_do_not_execute_property_or_body():
    result = analyze("""class Demo { int Delay {get { Thread.Sleep(999); return 1; }}
        Action task=()=>Thread.Sleep(999);
        public int DoWork() { var name=nameof(Delay); Action other=()=>Thread.Sleep(999);
        Thread.Sleep(7); return 0; } }""")
    assert result["total_ms"] == 7
    assert not any(stage.get("milliseconds") == 999 for stage in result["stages"])


def test_runtime_property_override_cannot_use_base_timing():
    result = analyze("""class Base { public virtual int Delay {get {return 5;}} }
        class Actual:Base { public override int Delay {get {return 1;}} }
        class Demo { Base item; public int DoWork() { Thread.Sleep(item.Delay); return 0; } }""")
    assert result["total_ms"] is None
    assert result["known_delay_min_ms"] == 0
    assert any(stage["kind"] == "unresolved" for stage in result["stages"])


def test_virtual_method_return_value_cannot_be_used_as_fixed_wait_parameter():
    result = analyze("""class Base { public virtual int Delay() {return 9;} }
        class Actual:Base { public override int Delay() {return 1;} }
        class Demo { Base item; public int DoWork() {Thread.Sleep(item.Delay()); return 0;} }""")
    assert result["known_delay_min_ms"] == 0 and result["known_delay_max_ms"] is None


def test_increment_runs_both_accessors_and_plain_local_assignment_is_not_doubled():
    changed = analyze("""class Motor { public int Position {get {Thread.Sleep(3);return 5;}
        set {Thread.Sleep(value);}} } class Demo { Motor motor; public int DoWork() {
        motor.Position++; return 0; } }""")
    assert changed["total_ms"] == 9
    scalar = analyze("""class Demo { public int DoWork() {int delay=5; delay=delay+2;
        Thread.Sleep(delay); return 0;} }""")
    assert scalar["total_ms"] == 7


def test_declared_base_variable_with_new_derived_is_not_treated_as_base_instance():
    result = analyze("""class Base {public virtual int Delay {get {return 9;}}}
        class Actual:Base {public override int Delay {get {return 1;}}}
        class Demo {public int DoWork() {Base item=new Actual();
        Thread.Sleep(item.Delay); return 0;}}""")
    assert result["total_ms"] is None and result["known_delay_min_ms"] == 0


def test_loop_counter_shadows_the_same_named_member_initializer():
    result = analyze("""class Demo {int i=100; public int DoWork() {
        for(int i=0;i<3;i++) Thread.Sleep(i); return 0;}}""")
    # 循环实际读取0、1、2；不读取同名成员的100，也不再遗漏可算计数器。
    assert result["total_ms"] == 3


def test_derived_property_body_and_hidden_field_do_not_reuse_base_initializer():
    explicit = analyze("""class Base {public virtual int Delay {get;}=9;}
        class Actual:Base {public override int Delay {get {return 1;}}}
        class Demo {Actual item; public int DoWork() {Thread.Sleep(item.Delay);return 0;}}""")
    assert explicit["total_ms"] == 1
    hidden = analyze("""class Base {public int Delay=9;}
        class Actual:Base {public new int Delay;}
        class Demo {Actual item; public int DoWork() {Thread.Sleep(item.Delay);return 0;}}""")
    assert hidden["total_ms"] is None


def test_static_type_receiver_and_cast_type_are_not_executed_as_properties():
    result = analyze("""class Settings {public static Settings GetInstance(){return null;}}
        class Demo {object data; Settings Settings=>Settings.GetInstance();
        Settings Other=>data as Settings;
        public int DoWork() {var a=Settings; var b=Other; var c=(Settings)data;
        Thread.Sleep(7);return 0;}}""")
    assert result["total_ms"] == 7 and not result["truncated"]


def test_conditional_getter_and_call_arguments_are_only_charged_on_nonnull_branch():
    getter = analyze("""class Settings {public int Delay {get {Thread.Sleep(5);return 1;}}}
        class Demo {Settings data; public int DoWork() {
        var x=data?.Delay;Thread.Sleep(3);return 0;}}""")
    assert (getter["known_delay_min_ms"], getter["known_delay_max_ms"]) == (3, 8)
    called = analyze("""class Settings {public void Pause(int ms){Thread.Sleep(ms);}}
        class Demo {Settings data; int Argument(){Thread.Sleep(3);return 7;}
        public int DoWork(){data?.Pause(Argument());return 0;}}""")
    assert (called["known_delay_min_ms"], called["known_delay_max_ms"]) == (0, 10)
    known = analyze("""class Settings {public int Delay {get {Thread.Sleep(5);return 1;}}}
        class Demo {public int DoWork(){var data=new Settings();var x=data?.Delay;
        Thread.Sleep(3);return 0;}}""")
    assert known["total_ms"] == 8


def test_out_discard_has_no_expression_to_evaluate_and_does_not_crash():
    result = analyze("""class Demo {Dictionary<int,int> values;
        public int DoWork(){values.TryGetValue(1,out _);Thread.Sleep(7);return 0;}}""")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 7


def test_catalog_reaches_setter_from_manual_assignment(tmp_path):
    (tmp_path / "Manual.cs").write_text(
        """class Motor { Axis axis;
        public int Position {set {axis.AbsoluteMove(value);}} }
        class Manual { Motor motor; void Click() {motor.Position=7;} }""",
        encoding="utf-8",
    )
    rows = SourceTiming(Workspace(tmp_path)).summary()["rows"]
    assert {("Motor", "set_Position"), ("Manual", "Click")} <= {
        (row["class_name"], row["method"]) for row in rows
    }
    assert next(row for row in rows if row["class_name"] == "Manual")["motion_count"] == 1
