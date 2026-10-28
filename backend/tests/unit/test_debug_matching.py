"""功能名称不能冒充明确的S区归属，也不能消除真正的条件冲突。"""

import pytest

from app.modules.knowledge.debug_matching import compatibility, explicit_filters


def record(module):
    return {
        "title": "中转台取片记录",
        "payload": {
            "module": module,
            "device": "ZX2200 HS",
            "software_version": "2.1.0",
            "conditions": "加热",
        },
    }


@pytest.mark.parametrize("module", ["中转台取片", "UPH与动作时序分析", "", "S10控制"])
def test_stage_is_unknown_when_only_function_or_other_identifier_is_recorded(module):
    result = compatibility(record(module), explicit_filters("ZX2200 HS V2.1.0 S2 加热取片"))
    assert result["status"] == "needs_confirmation"
    assert result["missing"] == ["module"]
    assert "module" not in result["matched"]


@pytest.mark.parametrize("module", ["S2固晶", "s2", "S1/S2共享中转台"])
def test_explicit_matching_stage_still_matches(module):
    result = compatibility(record(module), explicit_filters("ZX2200 HS V2.1.0 S2 加热取片"))
    assert result["status"] == "matched"
    assert "module" in result["matched"]


@pytest.mark.parametrize(
    ("module", "question"),
    [
        ("S1点胶", "ZX2200 HS V2.1.0 S2 加热取片"),
        ("中转台取片", "ZX2300 V2.1.0 S2 加热取片"),
        ("中转台取片", "ZX2200 HS V3.0.0 S2 加热取片"),
        ("中转台取片", "ZX2200 HS V2.1.0 S2 不加热取片"),
        ("中转台取片", "中转台取片"),
    ],
)
def test_other_explicit_conflicts_are_not_relaxed(module, question):
    filters = explicit_filters(question)
    if question == "中转台取片":
        filters["module"] = "点胶"
    assert compatibility(record(module), filters)["status"] == "mismatch"
