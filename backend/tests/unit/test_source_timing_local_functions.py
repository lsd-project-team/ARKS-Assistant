"""本地函数只有调用才执行，捕获的变量仍属于声明它的词法作用域。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    "body,expected",
    [
        ("void Never(){Thread.Sleep(999);}Thread.Sleep(7);", 7),
        ("void Step(){Thread.Sleep(20);}Step();Step();", 40),
        ("Step();void Step(){Thread.Sleep(30);}", 30),
        ("int delay=7;void Step(){Thread.Sleep(delay);}Step();delay=13;Step();", 20),
        ("int delay=7;void Step(){delay=11;}Step();Thread.Sleep(delay);", 11),
        ("void Step(int delay=10){Thread.Sleep(delay);}Step();Step(delay:15);", 25),
        (
            "int delay=10;void Read(){Thread.Sleep(delay);}"
            "void Forward(int delay){Read();}Forward(50);",
            10,
        ),
        ("{void Step(){Thread.Sleep(10);}Step();}{void Step(){Thread.Sleep(20);}Step();}", 30),
        ("void Step(){Thread.Sleep(delay);}int delay=20;Step();", 20),
    ],
)
def test_local_function_execution_and_lexical_values(body, expected):
    result = analyze("class Demo {public int DoWork(){" + body + "return 0;}}")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected
    assert result["total_ms"] == expected


def test_ref_and_out_arguments_and_captured_writes_are_transferred_back():
    result = analyze("""class Demo {public int DoWork(){int value=3,after;
        void Change(ref int input,out int output){Thread.Sleep(2);input=9;output=11;}
        Change(output:out after,input:ref value);Thread.Sleep(value+after);return 0;}}""")
    assert result["total_ms"] == 22


@pytest.mark.parametrize(
    "call",
    [
        "Run(Step);",
        "Action callback=Step;callback();",
        "new System.Windows.Forms.Control().Invoke((Action)Step);",
    ],
)
def test_a_local_function_can_be_forwarded_as_a_bound_delegate(call):
    result = analyze(
        """using System;using System.Windows.Forms;class Demo {
        void Run(Action callback){callback();}public int DoWork(){int delay=20;
        void Step(){Thread.Sleep(delay);}"""
        + call
        + "return 0;}}"
    )
    assert result["known_delay_min_ms"] == 20
    assert result["known_delay_max_ms"] == (None if "Control" in call else 20)
    assert any(
        stage["kind"] == "delay" and stage.get("milliseconds") == 20 and not stage["background"]
        for stage in result["stages"]
    )


def test_escaping_local_functions_keep_separate_parameter_frames():
    result = analyze("""using System;class Demo {Func<int> Make(int value){
        int Read()=>value;return Read;}public int DoWork(){
        var first=Make(3);var second=Make(5);Thread.Sleep(first()+second());return 0;}}""")
    assert result["total_ms"] == 8


def test_an_escaped_local_function_uses_lexical_siblings_after_its_block_exits():
    result = analyze("""using System;class Demo {Func<int> Make(int value){
        int Read()=>value;int Forward()=>Read();return Forward;}public int DoWork(){
        var first=Make(3);var second=Make(5);Thread.Sleep(first()+second());return 0;}}""")
    assert result["total_ms"] == 8


def test_the_current_class_member_is_used_after_a_local_function_scope_exits():
    result = analyze("""class Demo {void Step(){Thread.Sleep(30);}public int DoWork(){
        {void Step(){Thread.Sleep(10);}Step();}Step();return 0;}}""")
    assert result["total_ms"] == 40


def test_a_recursive_local_function_keeps_an_unresolved_completion_boundary():
    result = analyze("""class Demo {public int DoWork(){void Retry(){Thread.Sleep(1);Retry();}
        Retry();return 0;}}""")
    assert result["total_ms"] is None
    assert result["truncated"]


def test_a_never_called_sensor_check_does_not_create_a_wait():
    result = analyze("""class Sensor {public bool Check(){Thread.Sleep(400);return true;}}
        class Demo {Sensor sensor;public int DoWork(){void CheckMagazine(){
        if(!sensor.Check())CheckMagazine();}return 0;}}""")
    assert result["total_ms"] == 0
    assert not result["stages"]


@pytest.mark.parametrize(
    "body,expected",
    [
        ("const int delay=20;static void Read(){Thread.Sleep(delay);}Read();", 20),
        ("static int Read(int value)=>value;Thread.Sleep(Read(12));", 12),
        ("int delay=5;void Read(){Thread.Sleep(delay);void Other(){int delay=999;}}Read();", 5),
        ("int delay=10;void First(){void Second(){Thread.Sleep(delay);}Second();}First();", 10),
    ],
)
def test_nested_and_static_function_capture_boundaries(body, expected):
    result = analyze("class Demo {public int DoWork(){" + body + "return 0;}}")
    assert result["total_ms"] == expected


def test_functions_created_on_separate_loop_iterations_keep_separate_local_cells():
    result = analyze("""using System;class Demo {public int DoWork(){var callbacks=new Func<int>[2];
        for(int i=0;i<2;i++){int value=i+2;int Read()=>value;callbacks[i]=Read;}
        Thread.Sleep(callbacks[0]()+callbacks[1]());return 0;}}""")
    assert result["total_ms"] == 5


def test_a_lambda_returned_from_the_function_scope_can_still_call_its_lexical_function():
    result = analyze("""using System;class Demo {Func<int> Make(int value){
        int Read()=>value;return ()=>Read();}public int DoWork(){
        var first=Make(3);var second=Make(5);Thread.Sleep(first()+second());return 0;}}""")
    assert result["total_ms"] == 8


def test_a_function_declared_after_return_can_be_captured_before_the_declaration():
    result = analyze("""using System;class Demo {Func<int> Make(int value){return Read;
        int Read()=>value;}public int DoWork(){var callback=Make(7);
        Thread.Sleep(callback());return 0;}}""")
    assert result["total_ms"] == 7


def test_async_local_functions_preserve_their_task_result_and_completion():
    result = analyze("""using System.Threading.Tasks;class Demo {public int DoWork(){
        async Task<int> Read(){await Task.Delay(20);return 3;}
        Thread.Sleep(Read().GetAwaiter().GetResult());return 0;}}""")
    assert result["total_ms"] == 23


def test_nonstatic_local_functions_in_static_methods_can_capture_parameters():
    result = analyze("""class Demo {static int Read(int value){int Value()=>value;return Value();}
        public int DoWork(){Thread.Sleep(Read(11));return 0;}}""")
    assert result["total_ms"] == 11


@pytest.mark.parametrize("expression", ["delay", "Read()", "this.delay"])
def test_invalid_instance_capture_in_a_static_local_function_stays_unknown(expression):
    result = analyze(
        "class Demo {int delay=5;int Read()=>5;public int DoWork(){"
        "static int Value()=>" + expression + ";Thread.Sleep(Value());return 0;}}"
    )
    assert result["total_ms"] is None


def test_a_queued_lambda_can_call_a_local_function_with_a_constant_capture():
    result = analyze("""using System;class Demo {public int DoWork(){const int delay=20;
        void Step(){Thread.Sleep(delay);}Action wrapper=()=>Step();
        IAsyncResult pending=wrapper.BeginInvoke(null,null);
        wrapper.EndInvoke(pending);return 0;}}""")
    assert result["total_ms"] == 20


def test_the_delegate_array_receiver_and_index_are_evaluated_only_once():
    result = analyze("""using System;class Demo {public int DoWork(){
        int Read(){Thread.Sleep(20);return 0;}
        var callbacks=new Func<int>[] {Read};int index=0;
        callbacks[index++]();Thread.Sleep(index);return 0;}}""")
    assert result["total_ms"] == 21


def test_argument_evaluation_cannot_replace_the_already_read_array_delegate():
    result = analyze("""using System;class Demo {public int DoWork(){
        int First(int n){Thread.Sleep(20);return 0;}int Next(int n){Thread.Sleep(30);return 0;}
        var callbacks=new Func<int,int>[] {First};int Change(){callbacks[0]=Next;return 1;}
        callbacks[0](Change());callbacks[0](0);return 0;}}""")
    assert result["total_ms"] == 50


@pytest.mark.parametrize(
    "body,found",
    [
        ("void Never(){Thread.Sleep(999);}", False),
        ("void Step(){Thread.Sleep(20);}Step();", True),
        ("void Step(){Thread.Sleep(20);}Task.Run(Step);", True),
        ("void Step(){Thread.Sleep(20);}Hold(Step);", False),
    ],
)
def test_catalog_links_called_local_functions_without_promoting_unused_declarations(body, found):
    from app.modules.action_timing.source_catalog import build_catalog
    from app.modules.action_timing.source_index import SourceIndex

    source = "using System;using System.Threading.Tasks;class Demo {"
    source += "void Hold(Action value){}void Work(){" + body + "}}"
    index = SourceIndex([{"path": "main.cs", "content": source, "version": "test"}])
    entries, coverage = build_catalog(index, [])
    assert any(entry.method.name == "Work" for entry in entries) == found
    assert len(coverage["local_functions"]) == 1
    assert coverage["local_functions"][0]["linked_execution"] == found
    assert not any(entry.method.callable_kind == "local_function" for entry in entries)


def test_an_unused_local_delay_does_not_change_the_remaining_pure_call_bound():
    result = analyze("""class Demo {void Pure(){void Never(){Thread.Sleep(999);}}
        public int DoWork(){for(int i=0;i<130;i++)Pure();return 0;}}""")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 0
    assert result["total_ms"] is None and result["truncated"]


@pytest.mark.parametrize("kind", ["int", "var"])
def test_inline_out_local_keeps_the_called_body_delay_and_returned_value(kind):
    result = analyze(
        "class Demo {public int DoWork(){"
        "bool Locate(out int elapsed){Thread.Sleep(15);elapsed=7;return true;}"
        f"Locate(out {kind} elapsed);Thread.Sleep(elapsed);return 0;}}}}"
    )
    assert result["total_ms"] == 22


def test_inline_out_declaration_shadows_a_field_only_within_its_block():
    result = analyze("""class Demo {int elapsed=40;public int DoWork(){
        void Locate(out int value){Thread.Sleep(15);value=7;}
        {Locate(value:out int elapsed);Thread.Sleep(elapsed);}
        Thread.Sleep(elapsed);return 0;}}""")
    assert result["total_ms"] == 62


def test_separate_blocks_can_declare_the_same_out_variable_name():
    result = analyze("""class Demo {public int DoWork(){
        void Read(int value,out int result){result=value;}
        {Read(3,out var value);Thread.Sleep(value);}
        {Read(5,out int value);Thread.Sleep(value);}return 0;}}""")
    assert result["total_ms"] == 8


def test_an_out_declaration_in_a_loop_body_keeps_separate_escaped_cells():
    result = analyze("""using System;class Demo {public int DoWork(){
        void Read(int value,out int result){result=value;}
        var callbacks=new Func<int>[2];for(int i=0;i<2;i++){
            Read(i+2,out int value);int Get()=>value;callbacks[i]=Get;
        }Thread.Sleep(callbacks[0]()+callbacks[1]());return 0;}}""")
    assert result["total_ms"] == 5


@pytest.mark.parametrize(
    "expression", ["false && Read(out int value)", "true || Read(out int value)"]
)
def test_short_circuit_does_not_execute_an_inline_out_call(expression):
    result = analyze(
        "class Demo {public int DoWork(){bool Read(out int result){"
        "Thread.Sleep(999);result=9;return true;}"
        f"bool skip={expression};Thread.Sleep(3);return 0;}}}}"
    )
    assert result["total_ms"] == 3


@pytest.mark.parametrize("argument", ["out int _", "out var _"])
def test_an_out_discard_does_not_capture_or_replace_a_field_named_underscore(argument):
    result = analyze(
        "class Demo {int _=7;public int DoWork(){void Read(out int result){"
        "Thread.Sleep(15);result=99;}"
        f"Read({argument});Thread.Sleep(_);return 0;}}}}"
    )
    assert result["total_ms"] == 22


def test_a_plain_out_underscore_binds_an_existing_field_with_that_name():
    result = analyze("""class Demo {int _=7;public int DoWork(){
        void Read(out int result){Thread.Sleep(15);result=99;}
        Read(out _);Thread.Sleep(_);return 0;}}""")
    assert result["total_ms"] == 114


def test_a_plain_out_underscore_without_an_existing_variable_is_a_discard():
    result = analyze("""class Demo {public int DoWork(){
        void Read(out int result){Thread.Sleep(15);result=99;}
        Read(out _);return 0;}}""")
    assert result["total_ms"] == 15


def test_an_out_declaration_does_not_evaluate_a_same_named_property_getter():
    result = analyze("""class Demo {int _ {get{Thread.Sleep(999);return 7;}}
        public int DoWork(){void Read(out int result){Thread.Sleep(15);result=99;}
        Read(out int _);return 0;}}""")
    assert result["total_ms"] == 15
    assert not any(stage["method"] == "Demo.get__" for stage in result["stages"])


def test_an_unresolved_out_call_does_not_invent_a_returned_value():
    result = analyze("""class Demo {public int DoWork(){
        Unknown(out int elapsed);Thread.Sleep(elapsed);return 0;}}""")
    assert result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage.get("milliseconds") is None for stage in result["stages"]
    )


def test_an_inline_out_from_an_if_condition_is_visible_in_the_surrounding_block():
    result = analyze("""class Demo {public int DoWork(){
        bool Read(out int result){result=7;return true;}
        int Get()=>value;if(Read(out int value))Thread.Sleep(Get());
        Thread.Sleep(value);return 0;}}""")
    assert result["total_ms"] == 14


def test_a_for_initializer_out_local_does_not_replace_a_same_named_field_after_the_loop():
    result = analyze("""class Demo {int value=40;public int DoWork(){
        void Read(out int result){result=2;}
        for(Read(out int value);value<4;value++)Thread.Sleep(value);
        Thread.Sleep(value);return 0;}}""")
    assert result["total_ms"] == 45


def test_a_while_condition_out_local_does_not_replace_a_field_after_the_loop():
    result = analyze("""class Demo {int value=40;public int DoWork(){int count=0;
        bool Read(out int result){count++;result=count;return count<3;}
        while(Read(out int value))Thread.Sleep(value);
        Thread.Sleep(value);return 0;}}""")
    assert result["total_ms"] == 43


def test_a_null_conditional_call_does_not_run_an_inline_out_target():
    result = analyze("""class Probe {public void Read(out int result){
        Thread.Sleep(999);result=9;}}class Demo {public int DoWork(){
        Probe probe=null;probe?.Read(out int value);Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] == 3


def test_an_inline_out_local_declared_inside_a_local_function_binds_its_own_storage():
    result = analyze("""class Demo {int value=40;void Read(out int result){result=7;}
        public int DoWork(){void Step(){Read(out int value);Thread.Sleep(value);}
        Step();Thread.Sleep(value);return 0;}}""")
    assert result["total_ms"] == 47
