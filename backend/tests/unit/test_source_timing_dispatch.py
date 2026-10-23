"""UI与同步上下文的回调执行边界；排队延时保持未定，异步体不并入发起者。"""

import json

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    "body",
    [
        "context.Send(_=>Thread.Sleep(7),null);",
        "context.Send(state:7,d:ms=>Thread.Sleep((int)ms));",
        "control.Invoke(new Action(()=>Thread.Sleep(7)));",
        "control.Invoke(new Action<int>(n=>Thread.Sleep(n)),new object[]{7});",
        "control.Invoke(args:new object[]{7},method:new Action<int>(n=>Thread.Sleep(n)));",
    ],
)
def test_synchronous_dispatch_exposes_callback_delays_without_guessing_queue_time(body):
    result = analyze(f"""using System.Threading;using System.Windows.Forms;
        class Demo {{SynchronizationContext context;Control control;
        public int DoWork(){{{body}return 0;}}}}""")
    assert result["known_delay_min_ms"] == 7
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
    delays = [row for row in result["stages"] if row["kind"] == "delay"]
    assert [row["milliseconds"] for row in delays] == [7]
    assert not delays[0]["background"]
    assert any(row["kind"] == "wait" and row.get("dispatch") for row in result["stages"])
    json.dumps(result)


@pytest.mark.parametrize(
    "body",
    [
        "context.Post(_=>Thread.Sleep(7),null);",
        "control.BeginInvoke(new Action(()=>Thread.Sleep(7)));",
        "control.BeginInvoke(new Action<int>(n=>Thread.Sleep(n)),7);",
    ],
)
def test_asynchronous_dispatch_keeps_the_callback_outside_caller_elapsed_time(body):
    result = analyze(f"""using System.Threading;using System.Windows.Forms;
        class Demo {{SynchronizationContext context;Control control;
        public int DoWork(){{{body}Thread.Sleep(3);return 0;}}}}""")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 3
    delays = [row for row in result["stages"] if row["kind"] == "delay"]
    assert [row["milliseconds"] for row in delays] == [7, 3]
    assert delays[0]["background"] and not delays[1]["background"]


def test_concrete_base_context_send_has_no_ui_queue_wait():
    result = analyze("""using System.Threading;class Demo {public int DoWork(){
        var context=new SynchronizationContext();context.Send(_=>Thread.Sleep(7),null);
        return 0;}}""")
    assert result["total_ms"] == 7


def test_synchronous_callback_return_value_can_feed_a_subsequent_delay():
    result = analyze("""using System.Windows.Forms;class Demo {Control control;
        public int DoWork(){int ms=(int)control.Invoke(new Func<int>(()=>{
        Thread.Sleep(2);return 11;}));Thread.Sleep(ms);return 0;}}""")
    assert result["known_delay_min_ms"] == 13
    assert result["total_ms"] is None


def test_synchronous_dispatch_returns_an_inner_task_without_joining_it():
    result = analyze("""using System.Windows.Forms;class Demo {Control control;
        public int DoWork(){control.Invoke(new Func<Task>(async()=>{
        Thread.Sleep(3);await Task.Delay(20);}));Thread.Sleep(7);return 0;}}""")
    assert result["known_delay_min_ms"] == 10
    assert any(row["background"] and row.get("milliseconds") == 20 for row in result["stages"])


def test_synchronous_callback_write_is_visible_after_it_returns():
    result = analyze("""using System.Threading;class Demo {int delay=5;
        SynchronizationContext context;public int DoWork(){context.Send(_=>delay=7,null);
        Thread.Sleep(delay);return 0;}}""")
    assert result["known_delay_min_ms"] == 7


@pytest.mark.parametrize(
    "body", ["context.Post(_=>delay=7,null);", "control.BeginInvoke(new Action(()=>delay=7));"]
)
def test_queued_shared_write_invalidates_the_callers_old_delay(body):
    result = analyze(f"""using System.Threading;using System.Windows.Forms;
        class Demo {{int delay=5;SynchronizationContext context;Control control;
        public int DoWork(){{{body}Thread.Sleep(delay);return 0;}}}}""")
    assert result["total_ms"] is None
    assert not any(
        row.get("milliseconds") == 5 for row in result["stages"] if row["kind"] == "delay"
    )


def test_queued_read_does_not_freeze_a_mutable_capture_before_later_writes():
    result = analyze("""using System.Threading;class Demo {SynchronizationContext context;
        public int DoWork(){int delay=5;context.Post(_=>Thread.Sleep(delay),null);
        delay=7;Thread.Sleep(3);return 0;}}""")
    delays = [row for row in result["stages"] if row["kind"] == "delay"]
    assert delays[0]["background"] and delays[0]["milliseconds"] is None
    assert result["known_delay_min_ms"] == 3


def test_inherited_form_dispatch_and_source_method_with_the_same_name_are_distinct():
    result = analyze("""using System.Windows.Forms;class Demo : Form {
        public int DoWork(){Invoke(new Action(()=>Thread.Sleep(7)));return 0;}}""")
    assert result["known_delay_min_ms"] == 7
    source = analyze("""class Control {public void Invoke(Action cb){Thread.Sleep(19);}}
        class Demo {public int DoWork(){new Control().Invoke(()=>Thread.Sleep(999));return 0;}}""")
    assert source["total_ms"] == 19


def test_null_conditional_control_skips_callback_argument_side_effects():
    result = analyze("""using System.Windows.Forms;class Demo {public int DoWork(){
        Control control=null;
        control?.Invoke(Read());Thread.Sleep(3);return 0;}
        Delegate Read(){Thread.Sleep(999);return new Action(()=>Thread.Sleep(7));}}""")
    assert result["total_ms"] == 3


@pytest.mark.parametrize("write", ["delay=Unknown();", "values[0]=7;", "values.Clear();"])
def test_queued_unknown_writes_and_collection_writes_do_not_leave_old_values(write):
    declarations = "int delay=5;List<int> values=new List<int>{5};"
    tail = (
        "Thread.Sleep(delay);"
        if "delay=" in write
        else ("Thread.Sleep(values.Count);" if "Clear" in write else "Thread.Sleep(values[0]);")
    )
    result = analyze(f"""using System.Threading;class Demo {{int Unknown(){{return External();}}
        public int DoWork(){{{declarations}var context=new SynchronizationContext();
        context.Post(_=>{{{write}}},null);{tail}return 0;}}}}""")
    assert result["total_ms"] is None


def test_read_only_queued_callback_does_not_invalidate_the_callers_values():
    result = analyze("""using System.Threading;class Demo {public int DoWork(){int delay=5;
        var context=new SynchronizationContext();context.Post(_=>Thread.Sleep(delay),null);
        Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 5


def test_queued_private_object_and_constant_capture_remain_calculable():
    result = analyze("""using System.Threading;class Box {public int Delay=7;}
        class Demo {public int DoWork(){const int delay=11;var context=new SynchronizationContext();
        context.Post(_=>{var box=new Box();Thread.Sleep(box.Delay+delay);},null);
        Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] == 3
    assert any(row["background"] and row.get("milliseconds") == 18 for row in result["stages"])


def test_queued_delegate_variable_with_a_later_assignment_does_not_use_the_old_target():
    result = analyze("""using System.Threading;class Demo {public int DoWork(){
        Action action=()=>Thread.Sleep(999);var context=new SynchronizationContext();
        context.Post(_=>action(),null);action=()=>Thread.Sleep(7);Thread.Sleep(3);return 0;}}""")
    assert not any(row.get("milliseconds") == 999 for row in result["stages"])


def test_queued_wrapper_preserves_an_unchanged_delegate_parameter():
    result = analyze("""using System.Threading;class Helper {SynchronizationContext context;
        public void Run(Action action){context.Post(_=>action(),null);}}
        class Demo {public int DoWork(){new Helper().Run(()=>Thread.Sleep(7));
        Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] == 3
    assert any(row["background"] and row.get("milliseconds") == 7 for row in result["stages"])


def test_source_override_is_not_replaced_by_a_framework_callback():
    result = analyze("""using System.Threading;class Custom:SynchronizationContext {
        public override void Send(SendOrPostCallback d,object state){Thread.Sleep(11);}}
        class Demo {public int DoWork(){SynchronizationContext context=new Custom();
        context.Send(_=>Thread.Sleep(999),null);return 0;}}""")
    assert result["total_ms"] is None
    assert not any(row.get("milliseconds") == 999 for row in result["stages"])


@pytest.mark.parametrize("argument", ["true", "new object[]{7,11}"])
def test_invalid_framework_callback_arguments_do_not_create_a_fixed_body_time(argument):
    result = analyze(f"""using System.Windows.Forms;class Demo {{Control control;
        public int DoWork(){{control.Invoke(new Action<int>(n=>Thread.Sleep(7)),{argument});
        return 0;}}}}""")
    assert result["known_delay_min_ms"] == 0 and result["total_ms"] is None


def test_dispatch_evaluates_arguments_once_and_keeps_the_original_method_group_receiver():
    result = analyze("""using System.Windows.Forms;class Worker {int delay;
        public Worker(int value){delay=value;}public void Work(int ignored){Thread.Sleep(delay);}}
        class Demo {Control control;Worker worker;
        int Change(){Thread.Sleep(2);worker=new Worker(999);return 0;}
        public int DoWork(){worker=new Worker(7);
        control.Invoke(new Action<int>(worker.Work),Change());return 0;}}""")
    assert result["known_delay_min_ms"] == 9
    assert not any(row.get("milliseconds") == 999 for row in result["stages"])


def test_send_async_action_only_exposes_its_synchronous_prefix():
    result = analyze("""using System.Threading;class Demo {SynchronizationContext context;
        public int DoWork(){context.Send(async _=>{Thread.Sleep(3);await Task.Delay(20);},null);
        Thread.Sleep(7);return 0;}}""")
    assert result["known_delay_min_ms"] == 10
    assert any(row["background"] and row.get("milliseconds") == 20 for row in result["stages"])


def test_waiting_for_the_posting_task_does_not_wait_for_the_queued_ui_callback():
    result = analyze("""using System.Threading;class Demo {SynchronizationContext context;
        public int DoWork(){Task.Run(()=>context.Post(_=>Thread.Sleep(7),null)).Wait();
        Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] == 3
    assert any(row["background"] and row.get("milliseconds") == 7 for row in result["stages"])


def test_explicit_join_after_invoke_owns_the_returned_inner_task_stages():
    result = analyze("""using System.Windows.Forms;class Demo {Control control;
        public int DoWork(){((Task)control.Invoke(new Func<Task>(async()=>{
        Thread.Sleep(3);await Task.Delay(20);}))).Wait();return 0;}}""")
    assert result["total_ms"] is None
    assert all(not row["background"] for row in result["stages"] if row["kind"] == "delay")


def test_method_invoker_and_state_callback_delegate_types_are_supported():
    result = analyze("""using System.Windows.Forms;using System.Threading;class Demo {
        Control control;
        public int DoWork(){control.Invoke((MethodInvoker)(()=>Thread.Sleep(7)));
        var context=new SynchronizationContext();
        context.Send(new SendOrPostCallback(ms=>Thread.Sleep((int)ms)),11);return 0;}}""")
    assert result["known_delay_min_ms"] == 18


@pytest.mark.parametrize("callback,background", [("OnUIThread", False), ("BeginOnUIThread", True)])
def test_actual_winforms_provider_dispatches_the_bound_action(callback, background):
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    source = (
        root / "trunk/AKRS.ZX2200/Infrastructure/EventBus/WinformPlatformProvider.cs"
    ).read_text(encoding="utf-8-sig")
    result = analyze(
        f"""using AKRS.ZX2200.Infrastructure.EventBus;class Demo {{public int DoWork(){{
        new WinFormsPlatformProvider().{callback}(()=>Thread.Sleep(7));Thread.Sleep(3);
        return 0;}}}}""",
        source,
    )
    delays = [
        row for row in result["stages"] if row["kind"] == "delay" and row.get("milliseconds") == 7
    ]
    assert len(delays) == 1 and delays[0]["background"] is background
    assert result["total_ms"] is None if not background else result["total_ms"] == 3


def test_specific_callback_overload_is_preferred_to_a_generic_delegate_parameter():
    result = analyze("""class Demo {void Run(Action callback){callback();}
        void Run(Delegate callback,params object[] args){Thread.Sleep(999);}
        public int DoWork(){Run(()=>Thread.Sleep(7));return 0;}}""")
    assert result["total_ms"] == 7


def test_queued_unknown_delegate_does_not_leave_a_fixed_field_value_for_the_caller():
    result = analyze("""using System.Threading;class Demo {int delay=5;Action action;
        public int DoWork(){var context=new SynchronizationContext();
        context.Post(_=>action(),null);Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert not any(row.get("milliseconds") == 5 for row in result["stages"])


def test_queued_callback_budget_exhaustion_invalidates_unvisited_shared_writes():
    result = analyze("""using System.Threading;class Demo {int delay=5;
        void Empty(){}void Change(){delay=0;}public int DoWork(){
        var context=new SynchronizationContext();context.Post(_=>{
        for(int n=0;n<130;n++)Empty();Change();},null);Thread.Sleep(delay);return 0;}}""")
    assert result["truncated"]
    assert not any(row.get("milliseconds") == 5 for row in result["stages"])


def test_a_constant_field_remains_known_inside_a_queued_callback():
    result = analyze("""using System.Threading;class Demo {const int Delay=7;
        public int DoWork(){var context=new SynchronizationContext();
        context.Post(_=>Thread.Sleep(Delay),null);Thread.Sleep(3);return 0;}}""")
    assert result["total_ms"] == 3
    assert any(row["background"] and row.get("milliseconds") == 7 for row in result["stages"])


def test_future_ref_reassignment_does_not_freeze_the_old_queued_delegate():
    result = analyze("""using System.Threading;class Demo {
        void Change(ref Action value){value=()=>Thread.Sleep(7);}public int DoWork(){
        Action action=()=>Thread.Sleep(999);var context=new SynchronizationContext();
        context.Post(_=>action(),null);Change(ref action);Thread.Sleep(3);return 0;}}""")
    assert not any(row.get("milliseconds") == 999 for row in result["stages"])


@pytest.mark.parametrize("write", ["values.Clear();", "values[0]=7;"])
def test_queued_collection_field_mutation_invalidates_its_old_contents(write):
    tail = "Thread.Sleep(values.Count);" if "Clear" in write else "Thread.Sleep(values[0]);"
    result = analyze(f"""using System.Threading;class Demo {{List<int> values=new List<int>{{5}};
        public int DoWork(){{var context=new SynchronizationContext();
        context.Post(_=>{{{write}}},null);{tail}return 0;}}}}""")
    assert result["total_ms"] is None
    assert not any(row.get("milliseconds") == 5 for row in result["stages"])


def test_callback_specificity_does_not_override_another_arguments_type_conflict():
    result = analyze("""class Demo {void Run(Action cb,bool value){Thread.Sleep(999);}
        void Run(Delegate cb,int value){Thread.Sleep(7);}
        public int DoWork(){Run(()=>{},7);return 0;}}""")
    assert result["total_ms"] == 7


def test_an_invalid_numeric_to_boolean_source_argument_does_not_run_the_body():
    result = analyze("""class Demo {void Run(bool value){Thread.Sleep(999);}
        public int DoWork(){Run(7);return 0;}}""")
    assert result["total_ms"] is None
    assert not any(row.get("milliseconds") == 999 for row in result["stages"])
