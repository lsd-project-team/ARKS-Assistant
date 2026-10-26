"""加深调用不能挤掉后续已知等待；独立路径的时长与阶段不能重复相加。"""

from types import SimpleNamespace

import pytest

from app.modules.action_timing import source_budget
from app.modules.action_timing.source_budget import CallBudget
from app.modules.action_timing.source_estimator import Estimator
from app.modules.action_timing.source_index import SourceIndex
from app.modules.action_timing.source_profile_refinement import refine


def stage(delay=None):
    return {
        "kind": "unresolved" if delay is None else "delay",
        "label": "分析调用数量保护" if delay is None else "固定等待",
        "path": "Demo.cs",
        "line": 1 if delay is None else delay + 1,
        "version": "fixture",
        "code": "Work()" if delay is None else f"Thread.Sleep({delay})",
        "conditions": [],
        "background": False,
        "method": "Demo.DoWork",
        **(
            {"analysis_limit": {"kind": "call_budget", "target": "Demo.Work"}}
            if delay is None
            else {"milliseconds": delay}
        ),
    }


def result(lower, status="partial", upper=None):
    return {
        "known_delay_min_ms": lower,
        "known_delay_max_ms": upper,
        "total_ms": None,
        "execution_status": status,
        "truncated": True,
        "stages": [stage(), stage(lower)] if lower is not None else [stage()],
        "parameters": [],
    }


@pytest.mark.parametrize(
    ("other_lower", "status", "upper", "expected"),
    [
        (10, "partial", None, 10),
        (5, "partial", None, 5),
        (2, "partial", None, 5),
        (None, "partial", None, 5),
        (100, "unavailable", None, 5),
        (10, "partial", 7, 5),
    ],
)
def test_only_compatible_stronger_bound_is_selected_without_adding_paths(
    other_lower, status, upper, expected
):
    initial = result(5, upper=upper)
    alternative = result(other_lower, status)
    deep = SimpleNamespace(component_methods={"deep": object()})
    overview = SimpleNamespace(
        component_methods={"overview": object()}, estimate=lambda _: alternative
    )
    estimator, chosen = refine(None, None, deep, initial, lambda _: overview)
    assert chosen["known_delay_min_ms"] == expected
    assert chosen["total_ms"] is None
    assert chosen["stages"] is (alternative if expected > 5 else initial)["stages"]
    assert set(estimator.component_methods) == {"deep", "overview"}
    assert overview.max_call_depth == 7
    if expected > 5:
        assert chosen["supplementary_stages"] is initial["stages"]
        assert {p["milliseconds"] for p in chosen["known_components"]} >= {5, 10}
    else:
        assert "supplementary_stages" not in chosen


@pytest.mark.parametrize("reason", ["no_delay", "no_budget_limit", "complete", "configured_depth"])
def test_refinement_does_not_repeat_unaffected_or_explicitly_limited_analysis(reason, monkeypatch):
    initial = result(0 if reason == "no_delay" else 5)
    if reason == "no_budget_limit":
        initial["stages"] = [stage(5)]
    if reason == "complete":
        initial["truncated"] = False
    if reason == "configured_depth":
        monkeypatch.setattr(source_budget, "MAX_CALL_DEPTH", 1)

    def forbidden(_):
        raise AssertionError("不应重复执行没有触发条件的分析")

    deep = SimpleNamespace(component_methods={})
    assert refine(None, None, deep, initial, forbidden) == (deep, initial)
    assert "analysis_passes" not in initial


def test_deep_auxiliary_calls_do_not_hide_later_repeated_waits():
    methods = "".join(f"void M{n}(){{M{n + 1}();}}" for n in range(10))
    code = (
        "class Demo{" + methods + "void M10(){}void Heavy(){for(int j=0;j<3;j++)M0();}"
        "void WaitPart(int delay){Thread.Sleep(delay);}public int DoWork(){Thread.Sleep(1);"
        "for(int i=0;i<5;i++){Heavy();WaitPart(10);}return 0;}}"
    )
    index = SourceIndex([{"path": "Demo.cs", "content": code, "version": "fixture"}])
    method = index.by_method[("Demo", "DoWork")][0]

    class Limited(Estimator):
        def __init__(self, source):
            super().__init__(source)
            self.budget = CallBudget(limit=100)

    deep = Limited(index)
    original = deep.estimate(method)
    assert 0 < original["known_delay_min_ms"] < 51 and original["truncated"]
    selected, combined = refine(index, method, deep, original, Limited)
    assert combined["known_delay_min_ms"] == 51
    assert combined["total_ms"] is None and combined["truncated"]
    assert combined["analysis_passes"]["selected_depth"] == 7
    assert sum(s.get("milliseconds") == 10 for s in combined["stages"]) == 5
    assert sum(s.get("milliseconds") == 10 for s in combined["supplementary_stages"]) < 5
    assert selected.budget.limit == 100
    assert source_budget.MAX_CALL_DEPTH == 32
    next_code = (
        "class Demo{" + methods + "void M10(){Thread.Sleep(7);}public int DoWork(){M0();return 0;}}"
    )
    following = SourceIndex([{"path": "Next.cs", "content": next_code, "version": "fixture"}])
    assert (
        Estimator(following).estimate(following.by_method[("Demo", "DoWork")][0])["total_ms"] == 7
    )


def test_summary_keeps_refined_bound_without_dumping_supplementary_phases(tmp_path, monkeypatch):
    from app.modules.action_timing import source_service
    from app.modules.source_analysis.workspace import Workspace

    class Limited(Estimator):
        def __init__(self, source):
            super().__init__(source)
            self.budget = CallBudget(limit=100)

    monkeypatch.setattr(source_service, "Estimator", Limited)
    methods = "".join(f"void M{n}(){{M{n + 1}();}}" for n in range(10))
    (tmp_path / "Demo.cs").write_text(
        "class Demo{" + methods + "void M10(){}void Heavy(){for(int j=0;j<3;j++)M0();}"
        "void WaitPart(int delay){Thread.Sleep(delay);}public int DoWork(){Thread.Sleep(1);"
        "for(int i=0;i<5;i++){Heavy();WaitPart(10);}return 0;}}",
        encoding="utf-8",
    )
    service = source_service.SourceTiming(Workspace(tmp_path))
    row = next(r for r in service.summary()["rows"] if r["method"] == "DoWork")
    assert row["known_delay_min_ms"] == 51 and row["total_ms"] is None
    assert "stages" not in row and "supplementary_stages" not in row
    detail = service.detail(row["id"])
    assert row["supplementary_stage_count"] == len(detail["supplementary_stages"]) > 0
    assert detail["missing_categories"] == ["analysis"]
    assert detail["analysis_passes"]["selected_depth"] == 7
