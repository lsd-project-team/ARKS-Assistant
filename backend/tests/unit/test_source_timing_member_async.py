"""异步目标的未知经过时间不等同于调用者的私有委托/结果已经被改写。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


def test_private_delegate_and_result_survive_a_partial_target_that_does_not_write_them(
    source_iteration_limit,
):
    source_iteration_limit(128)
    result = analyze("""using System;class Demo {private Action action;private IAsyncResult pending;
        void Empty(){}void Slow(){Thread.Sleep(20);for(int n=0;n<130;n++)Empty();}
        public int DoWork(){action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}""")
    assert any(stage.get("operation") == "end" for stage in result["stages"])
    assert any(
        stage["kind"] == "delay" and stage["milliseconds"] == 20 and not stage["background"]
        for stage in result["stages"]
    )
    assert result["total_ms"] is None


def test_a_second_partial_target_does_not_erase_the_first_private_handle_or_end_marker():
    result = analyze("""using System;class Demo {private Action first,second;
        private IAsyncResult a,b;void Empty(){}
        void MoveA(){Thread.Sleep(20);for(int n=0;n<130;n++)Empty();}
        void MoveB(){Thread.Sleep(30);for(int n=0;n<130;n++)Empty();}
        public int DoWork(){first=MoveA;second=MoveB;a=first.BeginInvoke(null,null);
        b=second.BeginInvoke(null,null);first.EndInvoke(a);second.EndInvoke(b);return 0;}}""")
    assert len([stage for stage in result["stages"] if stage.get("operation") == "end"]) == 2
    assert result["known_delay_min_ms"] == 30


@pytest.mark.parametrize("write", ["action=null;", "Change();", "External(ref action);"])
def test_a_possible_private_write_keeps_the_end_unresolved_even_when_it_is_after_the_budget(write):
    result = analyze(f"""using System;class Demo {{
        private Action action;private IAsyncResult pending;
        void Empty(){{}}void Change(){{action=null;}}void External(ref Action value){{value=null;}}
        void Slow(){{for(int n=0;n<130;n++)Empty();{write}}}
        public int DoWork(){{action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])
    assert result["total_ms"] is None


def test_a_known_forwarded_callback_is_included_in_possible_writes():
    result = analyze("""using System;class Demo {private Action action;private IAsyncResult pending;
        void Empty(){}void Run(Action callback){callback();}
        void Slow(){for(int n=0;n<130;n++)Empty();Run(()=>action=null);}
        public int DoWork(){action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


def test_an_opaque_callback_cannot_be_assumed_to_preserve_private_state():
    result = analyze("""using System;class Demo {private Action action,unknown;
        private IAsyncResult pending;void Empty(){}
        void Slow(){for(int n=0;n<130;n++)Empty();unknown();}
        public int DoWork(){action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


def test_public_delegate_fields_stay_uncertain_at_an_unexplored_boundary(source_iteration_limit):
    source_iteration_limit(128)
    result = analyze("""using System;class Demo {public Action action;private IAsyncResult pending;
        void Empty(){}void Slow(){for(int n=0;n<130;n++)Empty();}
        public int DoWork(){action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


@pytest.mark.parametrize(
    "launch",
    [
        "Action writer=Change;writer.BeginInvoke(null,null);",
        "Task.Run((Action)Change);",
        "ChangeLater();",
        "new System.Windows.Forms.Control().BeginInvoke((Action)Change);",
    ],
)
def test_an_earlier_background_writer_cannot_be_hidden_by_a_new_assignment(launch):
    result = analyze(f"""using System;using System.Threading.Tasks;class Demo {{
        private Action action;private IAsyncResult pending;void Empty(){{}}
        void Change(){{Thread.Sleep(100);action=null;}}
        async void ChangeLater(){{await Task.Delay(100);action=null;}}
        void Slow(){{Thread.Sleep(20);for(int n=0;n<130;n++)Empty();}}
        public int DoWork(){{{launch}action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


@pytest.mark.parametrize(
    "tail",
    [
        "Run(Safe);",
        "Action next=Safe;next=Change;next();",
        "Action next=Change;next.BeginInvoke(null,null);",
        "External((object)this);",
        "object alias=this;External(alias);",
        "new Foreign((object)this);",
        'var description=$"{this}";',
        'var description="value:"+this;',
        "Action next=Factory();next();",
        "External(AsObject());",
        "Holder.Instance=this;",
        "object alias=null;alias=this;External(alias);",
        "Forward(this);",
    ],
)
def test_hidden_callback_and_object_effects_remain_conservative(tail):
    result = analyze(f"""using System;class Demo {{
        private Action action;private IAsyncResult pending;void Empty(){{}}void Safe(){{}}
        void Change(){{action=null;}}void Run(Action callback){{callback=Change;callback();}}
        Action Factory(){{return Change;}}
        object AsObject(){{return this;}}
        void Forward(object value){{External(value);}}
        public override string ToString(){{action=null;return "changed";}}
        void Slow(){{for(int n=0;n<130;n++)Empty();{tail}}}
        public int DoWork(){{action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


def test_the_same_forwarding_lambda_keeps_distinct_callback_environments():
    result = analyze("""using System;class Demo {private Action action;private IAsyncResult pending;
        void Empty(){}void Safe(){}void Change(){action=null;}
        void Invoke(Action callback){callback();}
        void Forward(Action callback){Invoke(()=>callback());}
        void Slow(){for(int n=0;n<130;n++)Empty();Forward(Safe);Forward(Change);}
        public int DoWork(){action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


def test_a_virtual_callback_with_an_unproven_runtime_type_is_not_a_pure_target():
    result = analyze("""using System;class Demo {private Action action;private IAsyncResult pending;
        protected void Change(){action=null;}void Empty(){}
        public virtual void Move(){for(int n=0;n<130;n++)Empty();}
        public int DoWork(){action=Move;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}
        class Derived:Demo {public override void Move(){Change();}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


@pytest.mark.parametrize(
    "tail",
    [
        "Action unused=()=>action=null;",
        "Run(Safe);",
        "var reading=Value;",
    ],
)
def test_creation_only_callbacks_and_known_read_only_calls_do_not_erase_the_handle(
    tail, source_iteration_limit
):
    source_iteration_limit(128)
    result = analyze(f"""using System;class Demo {{private Action action;
        private IAsyncResult pending;
        int Value{{get{{return 3;}}}}void Empty(){{}}void Safe(){{}}
        void Run(Action callback){{callback();}}
        void Slow(){{Thread.Sleep(20);for(int n=0;n<130;n++)Empty();{tail}}}
        public int DoWork(){{action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}}}""")
    assert any(stage.get("operation") == "end" for stage in result["stages"])
    assert result["known_delay_min_ms"] == 20
    assert result["total_ms"] is None


@pytest.mark.parametrize("tail", ["Value=3;", "var reading=Value;", "pending=null;"])
def test_private_writes_through_accessors_and_result_fields_invalidate_the_end(tail):
    result = analyze(f"""using System;class Demo {{private Action action;
        private IAsyncResult pending;
        int Value{{get{{action=null;return 3;}}set{{action=null;}}}}void Empty(){{}}
        void Slow(){{for(int n=0;n<130;n++)Empty();{tail}}}
        public int DoWork(){{action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


def test_a_previously_started_read_only_task_allows_a_later_private_join():
    result = analyze("""using System;using System.Threading.Tasks;class Demo {
        private Action action;private IAsyncResult pending;void Empty(){}
        void Slow(){Thread.Sleep(20);for(int n=0;n<130;n++)Empty();}
        public int DoWork(){Task.Run((Action)Slow);action=Slow;
        pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}""")
    assert any(stage.get("operation") == "end" for stage in result["stages"])


@pytest.mark.parametrize(
    "first",
    [
        "Task.Run(()=>{Task.Run((Action)Safe);Thread.Sleep(1);})",
        "ReadLater()",
    ],
)
def test_joining_an_old_task_cannot_forget_a_more_recent_background_writer(first):
    result = analyze(f"""using System;using System.Threading.Tasks;class Demo {{
        private Action action;private IAsyncResult pending;void Empty(){{}}void Safe(){{}}
        async Task ReadLater(){{await Task.Delay(1);Task.Run((Action)Safe);}}
        void Change(){{Thread.Sleep(100);action=null;}}
        void Slow(){{Thread.Sleep(20);for(int n=0;n<130;n++)Empty();}}
        public int DoWork(){{Task earlier={first};Action writer=Change;
        writer.BeginInvoke(null,null);earlier.Wait();action=Slow;
        pending=action.BeginInvoke(null,null);action.EndInvoke(pending);return 0;}}}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


def test_a_null_callback_summary_cannot_replace_an_unknown_callback_summary():
    result = analyze("""using System;class Demo {private Action action,unknown;
        private IAsyncResult pending;void Empty(){}void Invoke(Action callback){callback?.Invoke();}
        void Slow(){for(int n=0;n<130;n++)Empty();Invoke(null);Invoke(unknown);}
        public int DoWork(){action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


def test_source_field_initializers_can_write_private_control_fields():
    result = analyze("""using System;class Demo {private Action action;private IAsyncResult pending;
        public static Demo current;public static int Reset(){current.action=null;return 0;}
        void Empty(){}void Slow(){for(int n=0;n<130;n++)Empty();new Box();}
        public int DoWork(){action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}
        class Box {int initialized=Demo.Reset();}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


@pytest.mark.parametrize(
    "classes",
    [
        "class Base {public Base(){Demo.Reset();}}class Box:Base {}",
        "class Box {public Box():this(Demo.Reset()){}Box(int value){}}",
    ],
)
def test_constructor_chains_are_included_in_private_write_summaries(classes):
    result = analyze(
        """using System;class Demo {private Action action;private IAsyncResult pending;
        public static Demo current;public static int Reset(){current.action=null;return 0;}
        void Empty(){}void Slow(){for(int n=0;n<130;n++)Empty();new Box();}
        public int DoWork(){action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}"""
        + classes
    )
    assert not any(stage.get("operation") == "end" for stage in result["stages"])


def test_read_only_source_overrides_do_not_imply_a_private_control_write():
    result = analyze("""using System;class Demo {private Action action;private IAsyncResult pending;
        Base service;void Empty(){}
        void Slow(){Thread.Sleep(20);for(int n=0;n<130;n++)Empty();service.Read();}
        public int DoWork(){action=Slow;pending=action.BeginInvoke(null,null);
        action.EndInvoke(pending);return 0;}}
        class Base {public virtual int Read(){return 1;}}
        class Derived:Base {public override int Read(){return 2;}}""")
    assert any(stage.get("operation") == "end" for stage in result["stages"])
    assert result["total_ms"] is None


@pytest.mark.parametrize(
    "wrapper",
    [
        "Task.Run(()=>{BODY});",
        "Action outer=()=>{BODY};outer.BeginInvoke(null,null);",
        "new System.Windows.Forms.Control().BeginInvoke((Action)(()=>{BODY}));",
        "Task.Run(async()=>{await Task.Delay(1);BODY});",
    ],
)
def test_a_background_target_does_not_treat_its_own_sequential_setup_as_a_race(wrapper):
    body = "action=Slow;pending=action.BeginInvoke(null,null);action.EndInvoke(pending);"
    result = analyze(
        """using System;using System.Threading.Tasks;class Demo {
        private Action action;private IAsyncResult pending;void Empty(){}
        void Slow(){Thread.Sleep(20);for(int n=0;n<130;n++)Empty();}
        public int DoWork(){"""
        + wrapper.replace("BODY", body)
        + "return 0;}}"
    )
    assert any(stage.get("operation") == "end" for stage in result["stages"])


@pytest.mark.parametrize(
    "body,expected", [("var reading=para.Delay;", 100), ("para.Delay=30;", None)]
)
def test_callback_capture_preserves_read_only_objects_but_invalidates_their_future_writes(
    body, expected
):
    result = analyze(
        """using System.Threading.Tasks;class Demo {
        public int DoWork(){var para=new Parameter{Delay=100};Task.Run(()=>{"""
        + body
        + """});
        Thread.Sleep(para.Delay);return 0;}}class Parameter {public int Delay=10;}"""
    )
    assert result["known_delay_max_ms"] == expected
    assert result["total_ms"] == expected


def test_a_new_background_target_still_sees_its_parent_as_a_possible_writer():
    result = analyze("""using System;using System.Threading.Tasks;class Demo {
        private Action action;private IAsyncResult pending;void Empty(){}
        void Slow(){Thread.Sleep(20);for(int n=0;n<130;n++)Empty();}
        public int DoWork(){Task.Run(()=>{Task.Run(()=>{
        action=Slow;pending=action.BeginInvoke(null,null);action.EndInvoke(pending);});
        action=null;});return 0;}}""")
    assert not any(stage.get("operation") == "end" for stage in result["stages"])
