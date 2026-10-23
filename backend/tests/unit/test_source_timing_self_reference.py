"""this传递的是当前对象；原对象后续的写入不能退回声明初值。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    "helpers,body",
    [
        ("", "Use(this);"),
        ("", "Use(arg:this);"),
        ("", "Use((this));"),
        ("", "var current=this;Use(current);"),
        ("Demo Self(){return this;}", "Use(Self());"),
        ("Demo Self()=>this;", "Use(Self());"),
        ("Demo Self(){return (this);}", "Use(Self());"),
        ("", "Demo Self()=>this;Use(Self());"),
        ("", "Func<Demo> self=()=>this;Use(self());"),
        ("", "Func<Demo> self=()=>{return this;};Use(self());"),
        ("", "Use((Demo)this);"),
        ("", "Use((Demo)(object)this);"),
        ("", "Use(this as Demo);"),
        ("", "Use(/*before*/this/*after*/);"),
        ("", "Use(arg:/*before*/this/*after*/);"),
        ("", "var current=/*before*/this/*after*/;Use(current);"),
        ("Task<Demo> Self()=>Task.FromResult(this);", "Use(Self().Result);"),
    ],
)
def test_current_object_survives_expression_wrappers_and_return_paths(helpers, body):
    result = analyze(
        "using System;using System.Threading.Tasks;class Demo {int delay=7;"
        "void Use(Demo arg){Thread.Sleep(arg.delay);}"
        + helpers
        + "public int DoWork(){delay=11;"
        + body
        + "return 0;}}"
    )
    assert result["total_ms"] == 11


def test_a_callee_writes_the_original_object_passed_as_this():
    result = analyze("""class Demo {int delay=7;void Change(Demo arg){arg.delay=13;}
        public int DoWork(){Change(this);Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 13


def test_constructor_arguments_keep_the_original_object():
    result = analyze("""class Writer {public Writer(Demo owner){Thread.Sleep(2);owner.delay=13;}}
        class Demo {public int delay=7;public int DoWork(){new Writer(this);
        Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 15


def test_argument_side_effects_update_the_object_without_replacing_its_reference():
    result = analyze("""class Demo {int delay=7;int Change(){delay=13;Thread.Sleep(2);return 1;}
        void Use(Demo arg,int value){Thread.Sleep(arg.delay);}
        public int DoWork(){Use(value:Change(),arg:this);return 0;}}""")
    assert result["total_ms"] == 15


def test_separate_instances_return_their_own_this_reference():
    result = analyze("""class Demo {int delay=7;Demo Self()=>this;
        void Use(Demo arg){Thread.Sleep(arg.delay);}public int DoWork(){
        var first=new Demo();var second=new Demo();first.delay=11;second.delay=17;
        Use(first.Self());Use(second.Self());return 0;}}""")
    assert result["total_ms"] == 28


def test_an_escaped_callback_keeps_the_instance_that_created_it():
    result = analyze("""using System;class Demo {int delay=7;Func<Demo> Self()=>()=>this;
        public int DoWork(){var first=new Demo();var second=new Demo();
        first.delay=11;second.delay=17;var one=first.Self();var two=second.Self();
        Thread.Sleep(one().delay+two().delay);return 0;}}""")
    assert result["total_ms"] == 28


def test_a_deferred_self_result_reads_later_writes_to_the_original_instance():
    result = analyze("""using System;class Demo {int delay=7;Func<Demo> Self()=>()=>this;
        public int DoWork(){var later=Self();delay=13;
        Thread.Sleep(later().delay);return 0;}}""")
    assert result["total_ms"] == 13


def test_assignment_through_a_self_return_updates_the_original_instance():
    result = analyze("""class Demo {int delay=7;Demo Self()=>this;public int DoWork(){
        Self().delay=13;Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 13


@pytest.mark.parametrize(
    "body",
    [
        "var values=new Demo[]{this};Thread.Sleep(values.Length+values[0].delay);",
        "var values=new Demo[,]{{this,this}};Thread.Sleep(values.Length+values[0,1].delay-1);",
        "var values=new List<Demo>{this};Thread.Sleep(values.Count+values[0].delay);",
        "var values=new List<Demo>{/*before*/this/*after*/};"
        "Thread.Sleep(values.Count+values[0].delay);",
        "var value=new Holder{Target=this};Thread.Sleep(value.Target.delay+1);",
    ],
)
def test_initializer_values_keep_their_object_reference_and_element_count(body):
    result = analyze(
        "using System.Collections.Generic;class Holder {public Demo Target;}"
        "class Demo {public int delay=7;public int DoWork(){delay=11;" + body + "return 0;}}"
    )
    assert result["total_ms"] == 12


def test_a_base_method_self_return_does_not_replace_hidden_field_owners():
    result = analyze("""class Base {public int delay=7;public Base Self()=>this;
        public void Change(){delay=13;}}
        class Demo:Base {public new int delay=11;public int DoWork(){Change();
        Thread.Sleep(Self().delay+delay);return 0;}}""")
    assert result["total_ms"] == 24


@pytest.mark.parametrize("use", ["Base value=this;", "Base value=(Base)this;"])
def test_upcasting_this_retains_the_instance_and_the_declared_member_lookup(use):
    result = analyze(
        "class Base {public int delay=7;}class Demo:Base {public new int delay=11;"
        "public int DoWork(){base.delay=13;" + use + "Thread.Sleep(value.delay+delay);return 0;}}"
    )
    assert result["total_ms"] == 24


@pytest.mark.parametrize("condition", ["this!=null", "this==current", "current==this"])
def test_plain_class_this_equality_uses_reference_identity(condition):
    result = analyze(
        "class Demo {public int DoWork(){var current=this;if("
        + condition
        + ")Thread.Sleep(3);else Thread.Sleep(999);return 0;}}"
    )
    assert result["total_ms"] == 3


def test_a_self_return_and_a_created_object_compare_by_identity_not_payload_shape():
    result = analyze("""class Demo {int delay=7;Demo Self()=>this;public int DoWork(){
        var current=new Demo();current.delay=11;var alias=current.Self();
        if(current==alias)Thread.Sleep(3);else Thread.Sleep(999);return 0;}}""")
    assert result["total_ms"] == 3


def test_separate_self_results_with_equal_fields_remain_different_objects():
    result = analyze("""class Demo {int delay=7;Demo Self()=>this;public int DoWork(){
        var first=new Demo();var second=new Demo();
        if(first.Self()==second.Self())Thread.Sleep(999);else Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] == 3


def test_an_unproved_downcast_of_this_does_not_invent_the_derived_object():
    result = analyze("""class Base {public int delay=7;public Derived Self()=>(Derived)this;}
        class Derived:Base {}class Demo {public int DoWork(){var value=new Base();
        Thread.Sleep(value.Self().delay);return 0;}}""")
    assert result["total_ms"] is None
    assert any("引用转换" in stage["label"] for stage in result["stages"])


@pytest.mark.parametrize("target", ["Base<string>", "Demo[]"])
def test_erased_generic_or_array_names_do_not_prove_a_this_reference_conversion(target):
    result = analyze(
        "class Base<T>{}class Demo:Base<int>{void Accept(object value){}public int DoWork(){"
        "Accept((" + target + ")(object)this);Thread.Sleep(7);return 0;}}"
    )
    assert result["total_ms"] is None
    assert any("引用转换" in stage["label"] for stage in result["stages"])


def test_null_conditional_access_to_this_is_known_to_be_nonnull():
    result = analyze("""class Demo {void Step(){Thread.Sleep(3);}public int DoWork(){
        this?.Step();return 0;}}""")
    assert result["total_ms"] == 3


def test_struct_this_does_not_alias_the_callers_value_as_a_reference_object():
    result = analyze("""struct Demo {public int delay;void Change(Demo other){other.delay=99;}
        public int DoWork(){delay=7;Change(this);Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert any(stage["kind"] == "unresolved" for stage in result["stages"])


def test_a_custom_equality_operator_is_not_replaced_with_reference_comparison():
    result = analyze("""class Demo {public static bool operator ==(Demo a,Demo b){
        Thread.Sleep(777);return true;}public static bool operator !=(Demo a,Demo b)=>false;
        public int DoWork(){var current=new Demo();if(this==current)Thread.Sleep(3);
        return 0;}}""")
    assert result["total_ms"] is None
    assert any(stage["kind"] == "unresolved" for stage in result["stages"])


@pytest.mark.parametrize(
    "call", ["Unknown(this);", "Unknown(new Demo[]{this});", "External.GetInstance(this);"]
)
def test_unbound_external_code_cannot_preserve_old_fields_of_an_escaped_this(call):
    result = analyze(
        "class Demo {int delay=7;public int DoWork(){" + call + "Thread.Sleep(delay);return 0;}}"
    )
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage.get("milliseconds") is None for stage in result["stages"]
    )


def test_an_unexpanded_source_call_cannot_preserve_fields_it_may_change_through_this():
    result = analyze("""class Demo {int delay=7;void Last(Demo owner){owner.delay=99;}
        void Forward(Demo owner,int n){if(n>0)Forward(owner,n-1);else Last(owner);}
        public int DoWork(){Forward(this,20);Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None and result["truncated"]
    assert any(
        stage["kind"] == "delay" and stage.get("milliseconds") is None for stage in result["stages"]
    )


def test_this_escape_is_transferred_back_from_an_invoked_source_helper():
    result = analyze("""class Demo {int delay=7;void Escape(Demo owner){Unknown(owner);}
        public int DoWork(){Escape(this);Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage.get("milliseconds") is None for stage in result["stages"]
    )


def test_one_branch_escaping_this_keeps_the_later_member_read_unknown():
    result = analyze("""class Demo {int delay=7;public int DoWork(bool flag){
        if(flag)Unknown(this);Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage.get("milliseconds") is None for stage in result["stages"]
    )


def test_waiting_an_old_task_cannot_clear_new_this_escape_markers():
    result = analyze("""using System.Threading.Tasks;class Demo {int delay=7;
        void Escape(){Unknown(this);}public int DoWork(){var other=new Demo();other.Escape();
        var old=Task.Run(()=>Thread.Sleep(3));Unknown(this);old.Wait();
        Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "delay"
        and stage["code"] == "Thread.Sleep(delay)"
        and stage.get("milliseconds") is None
        for stage in result["stages"]
    )


def test_this_escape_invalidates_reachable_objects_already_held_by_other_locals():
    result = analyze("""class Child {public int delay=7;}class Demo {Child child;
        public int DoWork(){child=new Child();child.delay=11;var alias=child;
        Unknown(this);Thread.Sleep(alias.delay);return 0;}}""")
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage.get("milliseconds") is None for stage in result["stages"]
    )


def test_this_escape_does_not_invalidate_an_unrelated_instance():
    result = analyze("""class Demo {int delay=7;void Escape(){Unknown(this);}
        public int DoWork(){var first=new Demo();var second=new Demo();second.delay=17;
        first.Escape();Thread.Sleep(second.delay);return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 17


def test_this_escape_follows_an_array_element_written_after_allocation():
    result = analyze("""class Demo {int delay=7;public int DoWork(){
        var values=new object[1];values[0]=this;Unknown(values);
        Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage.get("milliseconds") is None for stage in result["stages"]
    )


def test_unbound_this_identity_does_not_invent_an_additional_software_delay():
    result = analyze("""class Target {public Target Self()=>this;}
        class Demo {public int DoWork(Target target){target.Self();
        Thread.Sleep(20);return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 20


@pytest.mark.parametrize("initializer", ["new int[]{1}", "new List<int>{1}"])
def test_known_framework_collection_null_checks_use_reference_semantics(initializer):
    result = analyze(
        "using System.Collections.Generic;class Demo {public int DoWork(){var values="
        + initializer
        + ";if(values!=null)Thread.Sleep(3);else Thread.Sleep(999);return 0;}}"
    )
    assert result["total_ms"] == 3


def test_unparsed_external_equality_keeps_unrelated_known_delay_composition():
    result = analyze("""class Demo {int delay=7;public int DoWork(){delay=20;
        var point=new ExternalPoint();if(point==null){}Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 20


@pytest.mark.parametrize(
    "declarations,base",
    [
        ("interface IConfig {}", "IConfig"),
        ("using System.ComponentModel;", "INotifyPropertyChanged"),
        ("", "System.ComponentModel.INotifyPropertyChanged"),
    ],
)
def test_implemented_interfaces_do_not_invalidate_fields_after_a_plain_null_check(
    declarations, base
):
    result = analyze(
        declarations + "class Config:" + base + "{public int delay=100;public bool force=false;}"
        "class Component:Config{}class Demo {void Pick(Component component){"
        "if(component==null)return;if(component.force)Thread.Sleep(999);"
        "Thread.Sleep(component.delay);}public int DoWork(){Pick(new Component());return 0;}}"
    )
    assert result["total_ms"] == 100
    assert not any("相等运算" in stage["label"] for stage in result["stages"])


@pytest.mark.parametrize(
    "declarations",
    [
        "",
        "using System.ComponentModel;class INotifyPropertyChanged {"
        "public static bool operator ==(INotifyPropertyChanged a,INotifyPropertyChanged b){"
        "Thread.Sleep(777);return false;}"
        "public static bool operator !=(INotifyPropertyChanged a,INotifyPropertyChanged b)=>true;}",
    ],
)
def test_an_unresolved_or_source_class_base_is_not_whitelisted_as_a_framework_interface(
    declarations,
):
    result = analyze(
        declarations + "class Config:INotifyPropertyChanged{public int delay=100;}"
        "class Demo {public int DoWork(){var value=new Config();"
        "if(value==null)return 0;Thread.Sleep(value.delay);return 0;}}"
    )
    assert result["total_ms"] is None
    assert any("相等运算" in stage["label"] for stage in result["stages"])
