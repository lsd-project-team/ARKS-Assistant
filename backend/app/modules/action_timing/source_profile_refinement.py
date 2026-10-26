"""不同深度的独立分析取较强已知下界；不把两份执行轨迹相加。"""

import json

from app.modules.action_timing import source_budget
from app.modules.action_timing.source_components import calculated_stages, number


def signature(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def refine(index, method, estimator, result, factory):
    """有正数等待却耗尽调用额度时，避免深层辅助调用挤掉后续可算等待。"""
    depth = source_budget.MAX_CALL_DEPTH
    lower = result.get("known_delay_min_ms")
    limited = any(
        stage.get("analysis_limit", {}).get("kind") == "call_budget" for stage in result["stages"]
    )
    if not (
        result["truncated"]
        and number(lower)
        and lower > 0
        and limited
        and depth > 7
        and result.get("execution_status") == "partial"
    ):
        return estimator, result

    overview = factory(index)
    overview.max_call_depth = 7
    alternative = overview.estimate(method)
    other_lower = alternative.get("known_delay_min_ms")
    comparable = alternative.get("execution_status") == result.get("execution_status")
    compatible = all(
        upper is None or minimum is None or upper >= minimum
        for upper, minimum in (
            (result.get("known_delay_max_ms"), other_lower),
            (alternative.get("known_delay_max_ms"), lower),
        )
    )
    use_overview = comparable and compatible and number(other_lower) and other_lower > lower
    selected, chosen = (overview, alternative) if use_overview else (estimator, result)
    other = result if use_overview else alternative
    selected.component_methods.update(estimator.component_methods)
    selected.component_methods.update(overview.component_methods)
    chosen["analysis_passes"] = {
        "selected_depth": 7 if use_overview else depth,
        "comparable": comparable and compatible,
        "passes": [
            {
                "max_call_depth": maximum,
                "known_delay_min_ms": candidate.get("known_delay_min_ms"),
                "known_delay_max_ms": candidate.get("known_delay_max_ms"),
                "execution_status": candidate.get("execution_status"),
                "truncated": candidate["truncated"],
            }
            for maximum, candidate in ((depth, result), (7, alternative))
        ],
        "note": "两份分析基于同一源码、输入初值与模拟工况；采用有依据的较强已知下界，"
        "不把不同展开路径的耗时相加，也不宣称剩余调用已算完。",
    }
    # 主要轨迹保持完整一致；较深的参数、运动模型及等待依据另存，不能混成执行顺序。
    if use_overview:
        chosen["supplementary_stages"] = result["stages"]
    facts = calculated_stages(chosen["stages"])
    known = {signature(part) for part in facts}
    for part in calculated_stages(other["stages"]):
        identity = signature(part)
        if identity not in known:
            known.add(identity)
            facts.append(
                {
                    **part,
                    "note": "另一展开深度核对到的等待组成；可能与主轨迹重合，不能相加。",
                }
            )
    chosen["known_components"] = facts
    names = {parameter["name"] for parameter in chosen["parameters"]}
    chosen["parameters"].extend(p for p in other["parameters"] if p["name"] not in names)
    return selected, chosen
