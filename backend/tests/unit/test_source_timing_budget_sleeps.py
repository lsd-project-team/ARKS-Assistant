"""调用受限后仍保留正常完成必须经过的固定等待，不推断返回值和状态。"""

import pytest

from tests.unit.test_source_timing_call_budget import limited


def test_repeated_pick_and_bond_preserves_all_explicit_waits_after_call_limit():
    estimator, result = limited(
        """class Demo{
        void Pick(){Hardware.Move();Thread.Sleep(200);Thread.Sleep(100);Thread.Sleep(100);}
        void Bond(){Hardware.Move();Thread.Sleep(500);Thread.Sleep(500);}
        public int DoWork(){for(int i=0;i<100;i++){Pick();Bond();Thread.Sleep(100);}return 0;}}
        """,
        4,
    )
    assert estimator.budget.used == 4
    assert result["known_delay_min_ms"] == 150000
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
    assert result["truncated"]
    assert (
        sum(
            stage.get("milliseconds", 0) or 0
            for stage in result["stages"]
            if stage["kind"] == "delay" and not stage["background"]
        )
        == 150000
    )


@pytest.mark.parametrize(
    "call",
    [
        "Thread.Sleep(3)",
        "System.Threading.Thread.Sleep(3)",
        "global::System.Threading.Thread.Sleep(millisecondsTimeout:3)",
    ],
)
def test_direct_literal_wait_survives_without_more_method_execution(call):
    estimator, result = limited(
        f"class Demo{{void Leaf(){{{call};}}"
        "public int DoWork(){Leaf();Thread.Sleep(7);return 0;}}",
        0,
    )
    assert estimator.budget.used == 0
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None


def test_only_prefix_before_conditional_return_is_guaranteed():
    _, result = limited(
        """class Demo{void Leaf(bool skip){Thread.Sleep(2);
        if(skip)return;Thread.Sleep(1000);}
        public int DoWork(){Leaf(false);Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 9 and result["total_ms"] is None
    assert not any(stage.get("milliseconds") == 1000 for stage in result["stages"])


def test_unknown_callback_is_not_executed_by_literal_wait_summary():
    _, result = limited(
        """using System.Threading.Tasks;class Demo{void Leaf(){
        Task.Run(()=>Thread.Sleep(999));Thread.Sleep(3);}
        public int DoWork(){Leaf();Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None
    assert not any(stage.get("milliseconds") == 999 for stage in result["stages"])


def test_summary_does_not_invent_a_return_value():
    _, result = limited(
        """class Demo{int Leaf(){Thread.Sleep(3);return 999;}
        public int DoWork(){int n=Leaf();Thread.Sleep(n);Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage["milliseconds"] is None for stage in result["stages"]
    )


def test_summary_leaves_receiver_writes_unknown_but_preserves_local_values():
    _, result = limited(
        """class Demo{int delay=9;void Leaf(){delay=0;Thread.Sleep(3);}
        public int DoWork(){int own=7;Leaf();Thread.Sleep(delay);Thread.Sleep(own);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage["milliseconds"] is None for stage in result["stages"]
    )


def test_summary_does_not_preserve_an_old_ref_value():
    _, result = limited(
        """class Demo{void Leaf(ref int n){n=0;Thread.Sleep(3);}
        public int DoWork(){int n=9;Leaf(ref n);Thread.Sleep(n);Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage["milliseconds"] is None for stage in result["stages"]
    )


@pytest.mark.parametrize(
    "body",
    [
        "if(flag)return;Thread.Sleep(999);",
        "for(int i=0;i<3;i++)Thread.Sleep(999);",
        "goto end;Thread.Sleep(999);end:;",
        "throw new Exception();Thread.Sleep(999);",
        "Thread.Sleep(-1);Thread.Sleep(999);",
        "Thread.Sleep(-2);Thread.Sleep(999);",
        "Thread.Sleep(2147483648);Thread.Sleep(999);",
        "Thread.Sleep(wrongName:3);Thread.Sleep(999);",
    ],
)
def test_summary_does_not_count_waits_behind_unproven_control_or_invalid_sleep(body):
    _, result = limited(
        f"""class Demo{{bool flag;void Leaf(){{{body}}}
        public int DoWork(){{Leaf();Thread.Sleep(7);return 0;}}}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 7 and result["total_ms"] is None
    assert not any(stage.get("milliseconds") == 999 for stage in result["stages"])


def test_async_body_is_not_summarized_as_a_synchronous_method():
    _, result = limited(
        """using System.Threading.Tasks;class Demo{
        async Task Leaf(){await Task.Delay(1);Thread.Sleep(999);}
        public int DoWork(){Leaf();Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 7 and result["total_ms"] is None
    assert not any(stage.get("milliseconds") == 999 for stage in result["stages"])


def test_source_thread_name_does_not_turn_an_ordinary_call_into_fixed_wait():
    _, result = limited(
        """class Thread{public static void Sleep(int n){}}
        class Demo{void Leaf(){Thread.Sleep(999);System.Threading.Thread.Sleep(3);}
        public int DoWork(){Leaf();System.Threading.Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None


def test_unknown_sleep_parameter_does_not_hide_a_later_mandatory_literal():
    _, result = limited(
        """class Demo{void Leaf(int n){Thread.Sleep(n);Thread.Sleep(3);}
        public int DoWork(){Leaf(999);Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None


def test_summary_does_not_invalidate_an_unrelated_object():
    _, result = limited(
        """class Worker{public int delay=9;
        public void Leaf(){delay=0;Thread.Sleep(3);}}class Demo{public int DoWork(){
        var changed=new Worker();var other=new Worker();changed.Leaf();
        Thread.Sleep(changed.delay);Thread.Sleep(other.delay);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 12 and result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage["milliseconds"] is None for stage in result["stages"]
    )


@pytest.mark.parametrize(
    "literal, expected", [("0x64", 100), ("0b110_0100", 100), ("1_000", 1000), ("(3)", 3), ("0", 0)]
)
def test_summary_handles_csharp_int_literals(literal, expected):
    _, result = limited(
        f"""class Demo{{void Leaf(){{Thread.Sleep({literal});}}
        public int DoWork(){{Leaf();Thread.Sleep(7);return 0;}}}}""",
        0,
    )
    assert result["known_delay_min_ms"] == expected + 7 and result["total_ms"] is None


def test_thread_alias_does_not_hide_an_explicit_framework_sleep():
    _, result = limited(
        """using Thread=Clock;class Clock{public static void Sleep(int n){}}
        class Demo{void Leaf(){Thread.Sleep(999);System.Threading.Thread.Sleep(3);}
        public int DoWork(){Leaf();System.Threading.Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None


def test_summary_does_not_preserve_an_old_static_value():
    _, result = limited(
        """class Demo{static int delay=9;
        static void Leaf(){delay=0;Thread.Sleep(3);}
        public int DoWork(){Leaf();Thread.Sleep(delay);Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None
    assert any(
        stage["kind"] == "delay" and stage["milliseconds"] is None for stage in result["stages"]
    )


def test_summary_stops_before_an_unconditional_recursive_call():
    _, result = limited(
        """class Demo{void Leaf(){Thread.Sleep(3);Leaf();Thread.Sleep(999);}
        public int DoWork(){Leaf();Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None
    assert not any(stage.get("milliseconds") == 999 for stage in result["stages"])


def test_expression_bodied_method_preserves_its_direct_wait():
    _, result = limited(
        """class Demo{void Leaf()=>Thread.Sleep(3);
        public int DoWork(){Leaf();Thread.Sleep(7);return 0;}}""",
        0,
    )
    assert result["known_delay_min_ms"] == 10 and result["total_ms"] is None
