"""循环按源码逐次求值，初始化、条件、正文与更新分别计时。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("for(int i=-180;i<=180;i+=5){Thread.Sleep(500);}", 36500),
        ("for(int i=2;i<=10;i+=2){Thread.Sleep(i);}", 30),
        ("for(int i=5;i>0;--i){Thread.Sleep(i);}", 15),
        ("for(double x=0.5;x<=2;x+=0.5){Thread.Sleep((int)(x*10));}", 50),
        ("int i;for(i=0;i<3;i++){Thread.Sleep(i);}Thread.Sleep(i);", 6),
        ("int delay=1;for(int i=0;i<3;i++){Thread.Sleep(delay);delay+=2;}Thread.Sleep(delay);", 16),
        ("for(int i=0;i<5;i++){if(i==2)continue;Thread.Sleep(3);}", 12),
        ("for(int i=0;i<5;i++){Thread.Sleep(3);if(i==2)break;}Thread.Sleep(7);", 16),
        ("for(int i=0;i<5;i++){if(i==2)return 0;Thread.Sleep(3);}Thread.Sleep(999);", 6),
        ("for(int i=0;i<3;i++){for(int j=0;j<=i;j++){Thread.Sleep(2);}}", 12),
        ("for(int i=0;i<0;i++){Thread.Sleep(999);}Thread.Sleep(7);", 7),
        ("int stop=5;for(int i=0;i<stop;i++){Thread.Sleep(2);stop--;}", 6),
        ("for(int i=0;i<5;i++){Thread.Sleep(2);i++;}", 6),
        ("for(int i=0,j=2;i<3;i++,j+=2){Thread.Sleep(j);}", 12),
    ],
)
def test_for_loop_execution_and_exit_timing(body, expected):
    result = analyze(f"class Demo {{public int DoWork(){{{body}return 0;}}}}")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected
    assert result["total_ms"] == expected


def test_loop_initializer_condition_and_update_execute_at_their_source_positions():
    result = analyze("""class Demo {int counter;
        int Start(){Thread.Sleep(7);return 0;}
        bool Next(){Thread.Sleep(2);return counter<3;}
        int Advance(){Thread.Sleep(5);return 1;}
        public int DoWork(){for(counter=Start();Next();counter+=Advance()){Thread.Sleep(3);}
        return 0;}}""")
    assert result["total_ms"] == 39  # 7 + 4*2 + 3*(3+5)


def test_unknown_break_branch_keeps_both_exit_state_and_elapsed_range():
    result = analyze("""class Demo {bool stop;
        public int DoWork(){int delay=1;
        for(int i=0;i<3;i++){if(stop){delay=7;break;}delay=3;Thread.Sleep(5);}
        Thread.Sleep(delay);return 0;}}""")
    assert result["known_delay_min_ms"] == 0
    assert result["known_delay_max_ms"] is None
    assert result["total_ms"] is None  # 退出后的delay不是始终为3


def test_unknown_bound_still_executes_initializer_once_and_preserves_unresolved_loop():
    result = analyze("""class Demo {int count;int Start(){Thread.Sleep(7);return 0;}
        public int DoWork(){for(int i=Start();i<count;i++){Thread.Sleep(3);}return 0;}}""")
    assert result["known_delay_min_ms"] == 7
    assert result["known_delay_max_ms"] is None


@pytest.mark.parametrize("update", ["i+=0", "i--"])
def test_non_terminating_or_wrong_direction_loop_does_not_gain_a_finite_total(update):
    result = analyze(
        f"class Demo {{public int DoWork(){{for(int i=0;i<3;{update})"
        "{Thread.Sleep(2);}return 0;}}"
    )
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


def test_counter_integer_overflow_cannot_prove_a_finite_csharp_loop():
    result = analyze("""class Demo {public int DoWork(){
        for(int i=2147483646;i<=2147483647;i++){Thread.Sleep(2);}return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


def test_each_iteration_has_fresh_body_locals_for_captured_callbacks():
    result = analyze("""class Demo {public int DoWork(){Action first=null;
        for(int i=0;i<3;i++){int delay=i;if(i==0)first=()=>Thread.Sleep(delay);}
        first();return 0;}}""")
    assert result["total_ms"] == 0


def test_a_later_for_variable_does_not_replace_an_earlier_captured_variable():
    result = analyze("""class Demo {public int DoWork(){Action first=null;
        for(int i=0;i<3;i++){if(i==0)first=()=>Thread.Sleep(i);}
        for(int i=0;i<5;i++){}
        first();return 0;}}""")
    assert result["total_ms"] == 3


def test_repeated_creation_at_the_same_source_position_has_distinct_objects():
    result = analyze("""class Worker {public int Delay;}
        class Demo {public int DoWork(){Worker first=null,last=null;
        for(int i=1;i<=2;i++){last=new Worker {Delay=i};if(i==1)first=last;}
        Thread.Sleep(first.Delay);Thread.Sleep(last.Delay);return 0;}}""")
    assert result["total_ms"] == 3


def test_unknown_continue_branch_does_not_assume_one_post_loop_delay():
    result = analyze("""class Demo {bool skip;public int DoWork(){int delay=1;
        for(int i=0;i<3;i++){if(skip){delay=7;continue;}delay=3;}
        Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("int i;for(i=0;i<1000;i++){Thread.Sleep(2);}Thread.Sleep(i);", 3000),
        ("for(int i=0;i<1000;i++){Thread.Sleep(i);}", 499500),
        ("for(int i=1000;i>0;i-=2){Thread.Sleep(i/2);}", 125250),
        ("for(int i=0;i<1000;i++){Thread.Sleep(i);Thread.Sleep(999-i);}", 999000),
    ],
)
def test_large_pure_integer_loop_sums_each_delay_without_creating_thousands_of_stages(
    body, expected
):
    result = analyze(f"class Demo {{public int DoWork(){{{body}return 0;}}}}")
    assert result["total_ms"] == expected
    assert len(result["stages"]) < 10


def test_effectful_condition_getter_is_not_treated_as_a_constant_bound():
    result = analyze("""class Demo {int Limit {get{Thread.Sleep(2);return 1000;}}
        public int DoWork(){for(int i=0;i<Limit;i++){Thread.Sleep(1);}return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


def test_unknown_loop_bound_still_lists_the_update_delay():
    result = analyze("""class Demo {int limit;int Advance(){Thread.Sleep(5);return 1;}
        public int DoWork(){for(int i=0;i<limit;i+=Advance()){Thread.Sleep(0);}return 0;}}""")
    assert result["known_delay_max_ms"] is None
    assert any(stage.get("milliseconds") == 5 for stage in result["stages"])


def test_unknown_condition_with_break_does_not_report_zero_iterations_as_exact():
    result = analyze("""class Demo {bool ready;public int DoWork(){
        for(int i=0;ready;i++){Thread.Sleep(3);break;}return 0;}}""")
    stage = next(stage for stage in result["stages"] if stage["kind"] == "loop")
    assert stage["iterations"] is None and stage["bounded"] is True
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (0, 3)


def test_alias_of_counter_in_bound_cannot_prove_a_constant_large_iteration_count():
    result = analyze("""class Demo {void Run(ref int i,ref int bound){
        for(i=0;i<bound+1000;i++){Thread.Sleep(1);}}
        public int DoWork(){int value=0;Run(ref value,ref value);return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None
