"""订阅只保存处理器；触发时按快照、顺序和取消规则计算实际正文。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    "body,expected",
    [
        ("Action cb=null;cb+=A;cb+=B;cb();", 10),
        ("Action cb=A;cb+=B;", 0),
        ("Action cb=A;cb+=A;cb-=A;cb();", 3),
        ("Action cb=A;cb-=B;cb();", 3),
        ("Action cb=null;cb-=A;cb?.Invoke();Thread.Sleep(2);", 2),
        ("Action cb=A;cb+=null;cb-=null;cb();", 3),
        ("Action cb=A;cb-=A;cb?.Invoke();Thread.Sleep(2);", 2),
        ("Action cb=A;Action copy=cb;cb+=B;copy();cb();", 13),
        ("Action pair=A;pair+=B;Action cb=pair;cb+=pair;cb-=pair;cb();", 10),
        ("Action pair=A;pair+=B;Action cb=A;cb+=B;cb+=A;cb-=pair;cb();", 3),
        ("Action cb=(Action)A+(Action)B;cb();", 10),
        ("Action cb=A;cb=cb+B;cb=cb-A;cb.Invoke();", 7),
        ("Action a=A;Action b=B;Action cb=a+b;cb-=a+b;cb?.Invoke();Thread.Sleep(2);", 2),
    ],
)
def test_delegate_invocation_lists_are_immutable_and_remove_only_the_last_match(body, expected):
    result = analyze(
        "using System;class Demo {void A(){Thread.Sleep(3);}void B(){Thread.Sleep(7);}"
        "public int DoWork(){" + body + "return 0;}}"
    )
    assert result["total_ms"] == expected


def test_handlers_observe_writes_by_the_previous_handler():
    result = analyze("""using System;class Demo {public int DoWork(){int delay=3;
        Action cb=()=>delay=11;cb+=()=>Thread.Sleep(delay);cb();return 0;}}""")
    assert result["total_ms"] == 11


def test_handler_list_is_read_once_even_if_the_first_handler_unsubscribes_the_second():
    result = analyze("""using System;class Demo {public int DoWork(){Action cb=null;
        Action later=()=>Thread.Sleep(7);cb=()=>{cb-=later;Thread.Sleep(3);};cb+=later;
        cb();cb();return 0;}}""")
    assert result["total_ms"] == 13


def test_same_method_on_different_instances_is_not_the_same_subscription():
    result = analyze("""using System;class Target {public int delay;
        public void Step(){Thread.Sleep(delay);}}class Demo {public int DoWork(){
        var one=new Target{delay=3};var two=new Target{delay=7};Action cb=one.Step;
        cb+=two.Step;cb-=one.Step;cb();return 0;}}""")
    assert result["total_ms"] == 7


def test_multicast_func_uses_the_last_return_value_and_keeps_earlier_effects():
    result = analyze("""using System;class Demo {int A(){Thread.Sleep(3);return 5;}
        int B(){Thread.Sleep(7);return 11;}public int DoWork(){Func<int> cb=A;cb+=B;
        Thread.Sleep(cb());return 0;}}""")
    assert result["total_ms"] == 21


def test_multicast_func_task_waits_only_the_last_returned_task():
    result = analyze("""using System;using System.Threading.Tasks;class Demo {
        public int DoWork(){Func<Task> cb=()=>Task.Delay(100);cb+=()=>Task.Delay(7);
        cb().Wait();return 0;}}""")
    assert result["total_ms"] == 7
    assert any(
        s["kind"] == "delay" and s["milliseconds"] == 100 and s["background"]
        for s in result["stages"]
    )


def test_known_multicast_can_be_passed_to_a_source_helper():
    result = analyze("""using System;class Demo {void Use(Action cb){cb();}
        public int DoWork(){Action cb=()=>Thread.Sleep(3);cb+=()=>Thread.Sleep(7);
        Use(cb);return 0;}}""")
    assert result["total_ms"] == 10


def test_multicast_dynamic_invoke_executes_all_handlers_in_order():
    result = analyze("""using System;class Demo {public int DoWork(){
        Action<int> cb=n=>Thread.Sleep(n);cb+=n=>Thread.Sleep(n+1);
        cb.DynamicInvoke(new object[]{3});return 0;}}""")
    assert result["total_ms"] == 7


@pytest.mark.parametrize("kind", ["Action", "EventHandler", "Changed"])
def test_events_on_a_new_instance_start_empty_and_keep_explicit_subscription(kind):
    parameters = "" if kind == "Action" else "object sender,EventArgs args"
    arguments = "" if kind == "Action" else "this,EventArgs.Empty"
    declaration = (
        "delegate void Changed(object sender,EventArgs args);" if kind == "Changed" else ""
    )
    result = analyze(
        "using System;" + declaration + "class Source {public event " + kind + " Done;"
        "public void Fire(){Done?.Invoke("
        + arguments
        + ");}}class Demo {void Step("
        + parameters
        + "){Thread.Sleep(7);}public int DoWork(){var value=new Source();"
        "value.Fire();value.Done+=Step;value.Fire();value.Done-=Step;value.Fire();return 0;}}"
    )
    assert result["total_ms"] == 7


def test_event_subscribed_in_a_constructor_keeps_the_actual_receiver():
    result = analyze("""using System;class Source {public event Action Done;
        public Source(Action handler){Done+=handler;}public void Fire(){Done?.Invoke();}}
        class Demo {int delay=11;void Step(){Thread.Sleep(delay);}public int DoWork(){
        new Source(Step).Fire();return 0;}}""")
    assert result["total_ms"] == 11


def test_two_publishers_keep_separate_event_lists():
    result = analyze("""using System;class Source {public event Action Done;
        public void Fire(){Done?.Invoke();}}class Demo {public int DoWork(){
        var one=new Source();var two=new Source();one.Done+=()=>Thread.Sleep(3);
        two.Done+=()=>Thread.Sleep(7);one.Fire();return 0;}}""")
    assert result["total_ms"] == 3


def test_subscription_changes_do_not_invent_the_existing_public_event_list():
    result = analyze("""using System;class Demo {public event Action Done;
        public int DoWork(){Done+=()=>Thread.Sleep(7);Done?.Invoke();return 0;}}""")
    assert result["total_ms"] is None


def test_an_unknown_delegate_list_does_not_become_complete_after_a_known_subscription():
    result = analyze("""using System;class Demo {public int DoWork(Action cb){
        cb+=()=>Thread.Sleep(7);cb();return 0;}}""")
    assert result["total_ms"] is None


def test_an_async_event_handler_starts_its_task_without_adding_its_delay_to_the_publisher():
    result = analyze("""using System;using System.Threading.Tasks;class Source {
        public event Action Done;public void Fire(){Done?.Invoke();}}class Demo {
        public int DoWork(){var value=new Source();value.Done+=()=>Task.Run(async ()=>{
        await Task.Delay(500);Thread.Sleep(3);});value.Fire();Thread.Sleep(7);return 0;}}""")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 7
    assert any(
        s["kind"] == "delay" and s["milliseconds"] == 500 and s["background"]
        for s in result["stages"]
    )


@pytest.mark.parametrize(
    "body",
    [
        "Action a=A,b=A;if(a==b)Thread.Sleep(3);else Thread.Sleep(999);",
        "Action a=A,b=B;if(a!=b)Thread.Sleep(3);else Thread.Sleep(999);",
        "Action a=A,b=A;a+=B;b+=B;if(a==b)Thread.Sleep(3);else Thread.Sleep(999);",
        "Action a=A,b=A;a+=B;if(a!=b)Thread.Sleep(3);else Thread.Sleep(999);",
        "Action a=A;a-=A;if(a==null)Thread.Sleep(3);else Thread.Sleep(999);",
    ],
)
def test_delegate_equality_uses_handler_and_receiver_lists(body):
    result = analyze(
        "using System;class Demo {void A(){}void B(){}public int DoWork(){" + body + "return 0;}}"
    )
    assert result["total_ms"] == 3


def test_nullable_action_subscription_keeps_the_known_list():
    result = analyze("""using System;class Demo {public int DoWork(){
        Action? cb=null;cb+=()=>Thread.Sleep(7);cb?.Invoke();return 0;}}""")
    assert result["total_ms"] == 7


def test_existing_unknown_list_remains_unknown_after_removing_a_known_handler():
    result = analyze("""using System;class Demo {void A(){}public int DoWork(Action cb){
        cb-=A;cb?.Invoke();return 0;}}""")
    assert result["total_ms"] is None


@pytest.mark.parametrize("first", ["A", "()=>A()"])
def test_a_throwing_first_handler_does_not_execute_later_handlers(first):
    result = analyze(
        "using System;class Demo {void A(){throw new Exception();}"
        "void B(){Thread.Sleep(999);}public int DoWork(){Action cb="
        + first
        + ";cb+=B;cb();return 0;}}"
    )
    assert result["total_ms"] is None
    assert not any(s["kind"] == "delay" and s["milliseconds"] == 999 for s in result["stages"])


def test_a_delegate_field_initializer_is_applied_after_its_initial_empty_list():
    result = analyze("""using System;class Target {public Action Step=()=>Thread.Sleep(3);
        public Target(){Step+=()=>Thread.Sleep(7);}}class Demo {public int DoWork(){
        new Target().Step();return 0;}}""")
    assert result["total_ms"] == 10


def test_multicast_async_invoke_does_not_invent_a_supported_runtime_completion():
    result = analyze("""using System;class Demo {public int DoWork(){
        Action cb=()=>Thread.Sleep(3);cb+=()=>Thread.Sleep(7);
        var pending=cb.BeginInvoke(null,null);cb.EndInvoke(pending);return 0;}}""")
    assert result["total_ms"] is None
    assert not any(s.get("operation") == "end" for s in result["stages"])


def test_multicast_background_writes_include_the_first_handler_beyond_its_execution_budget():
    result = analyze("""using System;using System.Threading.Tasks;class Demo {
        private Action action;private IAsyncResult pending;void Empty(){}
        void Change(){for(int i=0;i<130;i++)Empty();action=null;}void Safe(){}
        void Slow(){Thread.Sleep(20);for(int i=0;i<130;i++)Empty();}
        public int DoWork(){Action writer=Change;writer+=Safe;Task.Run(writer);
        action=Slow;pending=action.BeginInvoke(null,null);action.EndInvoke(pending);return 0;}}""")
    assert result["total_ms"] is None
    assert not any(s.get("operation") == "end" for s in result["stages"])


def test_subscription_list_budget_does_not_silently_drop_handlers():
    result = analyze(
        "using System;class Demo {void A(){Thread.Sleep(1);}public int DoWork(){Action cb=null;"
        + "cb+=A;" * 129
        + "cb();return 0;}}"
    )
    assert result["total_ms"] is None


def test_subscription_receiver_is_evaluated_before_a_rhs_that_reassigns_its_variable():
    result = analyze("""using System;class Source {public event Action Done;
        public void Fire(){Done?.Invoke();}}class Demo {public int DoWork(){
        var one=new Source();var two=new Source();var current=one;
        Action Next(){current=two;return ()=>Thread.Sleep(7);}
        current.Done+=Next();one.Fire();return 0;}}""")
    assert result["total_ms"] == 7


def test_direct_delegate_field_invocation_reads_its_target_before_argument_side_effects():
    result = analyze("""using System;class Source {public Action<int> Step;}
        class Demo {public int DoWork(){var value=new Source();
        value.Step=n=>Thread.Sleep(7);int Change(){value.Step=n=>Thread.Sleep(999);return 1;}
        value.Step(Change());return 0;}}""")
    assert result["total_ms"] == 7


def test_direct_delegate_property_invocation_runs_its_getter_once():
    result = analyze("""using System;class Source {public Action Step {get{
        Thread.Sleep(3);return ()=>Thread.Sleep(7);}}}class Demo {
        public int DoWork(){new Source().Step();return 0;}}""")
    assert result["total_ms"] == 10


def test_a_source_class_named_eventhandler_is_not_treated_as_a_framework_delegate():
    result = analyze("""using System;class EventHandler {public void Invoke(){Thread.Sleep(7);}}
        class Demo {public int DoWork(){new EventHandler().Invoke();return 0;}}""")
    assert result["total_ms"] == 7


@pytest.mark.parametrize("unknown_write", [False, True])
def test_static_bridge_effects_follow_all_source_writes_without_binding_the_runtime_delegate(
    unknown_write,
):
    reset = "void Reset(){Send=External.Callback();}" if unknown_write else ""
    result = analyze(
        "using System;class Bridge {public static Action<Action> Send;"
        "public Bridge(){Send+=Post;}void Post(Action action){action();}" + reset + "}"
        "class Demo {private Action action;private IAsyncResult pending;void Empty(){}"
        "void Other(){Bridge.Send(()=>{});for(int i=0;i<130;i++)Empty();}"
        "void Slow(){Thread.Sleep(20);for(int i=0;i<130;i++)Empty();}"
        "public int DoWork(){Action writer=Other;writer.BeginInvoke(null,null);"
        "action=Slow;pending=action.BeginInvoke(null,null);action.EndInvoke(pending);return 0;}}"
    )
    assert any(s.get("operation") == "end" for s in result["stages"]) is not unknown_write
    assert result["total_ms"] is None


@pytest.mark.parametrize("modifier", ["ref", "out"])
def test_custom_delegate_reference_parameters_are_not_silently_treated_as_value_parameters(
    modifier,
):
    result = analyze(
        "delegate void Change("
        + modifier
        + " int value);class Demo {void Set("
        + modifier
        + " int value){value=11;}public int DoWork(){int delay=7;"
        "Change cb=Set;cb(" + modifier + " delay);Thread.Sleep(delay);return 0;}}"
    )
    assert result["total_ms"] is None


@pytest.mark.parametrize(
    "declaration,initialization,call",
    [
        (
            "delegate void Change(ref int value);",
            "Change cb=(ref int value)=>value=11;",
            "cb(ref delay);",
        ),
        (
            "delegate void Change<T>(T value);",
            "Change<int> cb=value=>Thread.Sleep(value);",
            "cb(7);",
        ),
    ],
)
def test_unsupported_custom_signatures_do_not_bypass_validation_through_a_lambda(
    declaration, initialization, call
):
    result = analyze(
        declaration
        + "class Demo {public int DoWork(){int delay=7;"
        + initialization
        + call
        + "Thread.Sleep(delay);return 0;}}"
    )
    assert result["total_ms"] is None


@pytest.mark.parametrize("declaration", ["private event Action Done;", "event Action Done;"])
@pytest.mark.parametrize("work", ["", "for(int i=0;i<130;i++)Empty();"])
def test_a_future_private_event_write_is_not_hidden_by_a_later_subscription_assignment(
    declaration, work
):
    result = analyze(
        """using System;using System.Threading.Tasks;class Demo {
        """
        + declaration
        + """void Empty(){}
        void Later(){"""
        + work
        + """Done=null;}
        public int DoWork(){Task.Run(Later);Done=()=>Thread.Sleep(7);
        Done?.Invoke();return 0;}}"""
    )
    assert result["total_ms"] is None
    assert result["known_delay_min_ms"] == 0
