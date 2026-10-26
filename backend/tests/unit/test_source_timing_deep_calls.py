"""正常长调用链不能被当作缺参；递归和预算保护仍须明确标识。"""

import pytest

from tests.unit.test_source_timing_call_budget import limited
from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize("depth", [7, 12, 24])
@pytest.mark.parametrize("callback", [False, True])
def test_finite_deep_call_chain_keeps_argument_delay_and_returned_value(depth, callback):
    methods = "".join(f"int M{n}(int delay){{return M{n + 1}(delay+1);}}" for n in range(depth))
    methods += f"int M{depth}(int delay){{Thread.Sleep(delay);return 3;}}"
    invoke = (
        "int result=M0(5);"
        if not callback
        else "int result=0;Action work=()=>{result=M0(5);};work();"
    )
    result = analyze(
        "using System;class Demo{"
        + methods
        + "public int DoWork(){"
        + invoke
        + "Thread.Sleep(result);return 0;}}"
    )
    assert result["total_ms"] == depth + 8
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == depth + 8
    assert not result["truncated"]


def test_deep_constructor_base_chain_keeps_all_fixed_waits():
    classes = "class Base0{public Base0(){Thread.Sleep(2);}}" + "".join(
        f"class Base{n}:Base{n - 1}{{public Base{n}(){{Thread.Sleep(2);}}}}" for n in range(1, 13)
    )
    result = analyze(classes + "class Demo{public int DoWork(){new Base12();return 0;}}")
    assert result["total_ms"] == 26
    assert not result["truncated"]


def test_finite_deep_calls_preserve_side_effects_and_unknown_branch():
    methods = "".join(f"void M{n}(){{M{n + 1}();}}" for n in range(12))
    result = analyze(
        "class Demo{int delay=1;"
        + methods
        + "void M12(){delay=9;}public int DoWork(){M0();Thread.Sleep(delay);"
        "if(Ready())Thread.Sleep(7);return 0;}extern bool Ready();}"
    )
    assert result["known_delay_min_ms"] == 9
    assert result["known_delay_max_ms"] == 16
    assert not result["truncated"]


def test_recursive_source_still_has_an_explicit_analyzer_requirement():
    result = analyze(
        "class Demo{void Again(){Thread.Sleep(2);Again();}public int DoWork(){Again();return 0;}}"
    )
    assert result["truncated"] and result["total_ms"] is None
    stage = next(s for s in result["stages"] if s.get("analysis_limit"))
    assert stage["analysis_limit"]["kind"] == "recursion"
    assert stage["definitions"][0]["code"].startswith("void Again")


def test_known_loop_count_beyond_body_limit_is_an_analysis_gap():
    from app.modules.action_timing.source_requirements import attach

    result = analyze(
        "class Demo{void Leaf(int n){Thread.Sleep(n);}"
        "public int DoWork(){for(int n=0;n<10000;n++)Leaf(n);return 0;}}"
    )
    attach(result)
    assert result["truncated"] and result["total_ms"] is None
    loop = next(s for s in result["stages"] if s["kind"] == "loop")
    assert loop["analysis_limit"]["kind"] == "loop_iterations"
    assert any(r["category"] == "analysis" for r in result["missing_requirements"])
    assert not any(r["category"] == "input" for r in result["missing_requirements"])


@pytest.mark.parametrize("count", [150, 600])
def test_proven_finite_for_can_use_the_shared_budget_to_finish(count):
    result = analyze(
        "class Demo{void Leaf(int n){Thread.Sleep(n);}"
        f"public int DoWork(){{for(int n=0;n<{count};n++)Leaf(n);return 0;}}}}"
    )
    assert result["total_ms"] == (11175 if count == 150 else 179700)
    assert not result["truncated"]


def test_body_counter_write_still_controls_actual_count():
    result = analyze(
        "class Demo{void Leaf(){Thread.Sleep(3);}"
        "public int DoWork(){for(int n=0;n<150;n++){Leaf();n++;}return 0;}}"
    )
    assert result["total_ms"] == 225
    assert not result["truncated"]


def test_call_budget_is_not_reported_as_missing_source_or_hardware():
    _, result = limited(
        "class Demo{void Leaf(){Thread.Sleep(3);}"
        "public int DoWork(){for(int n=0;n<10;n++)Leaf();return 0;}}",
        4,
    )
    assert result["known_delay_min_ms"] == 30 and result["total_ms"] is None
    from app.modules.action_timing.source_requirements import attach

    attach(result)
    boundary = next(s for s in result["stages"] if s.get("analysis_limit"))
    assert boundary["analysis_limit"]["kind"] == "call_budget"
    assert all(r["category"] == "analysis" for r in result["missing_requirements"])
    assert any(
        "不是缺少运行参数" in x for r in result["missing_requirements"] for x in r["required"]
    )
