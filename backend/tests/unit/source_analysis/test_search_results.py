"""检索定位片段的覆盖、截断和排序；不把路径启发式当成调用关系证明。"""

from collections import Counter

import pytest

from app.modules.source_analysis.search_results import select_matches


def hit(path, line=1):
    return {"path": path, "line": line, "text": f"真实片段 {line}"}


def test_dense_file_cannot_hide_later_entry_and_original_coordinates_are_retained():
    rows = [hit("Controllers/Legacy.cs", n) for n in range(1, 151)]
    rows += [hit("Flow/ProductionActionNode.cs", 77), hit("Tasks/WorkTask.cs", 31)]
    result = select_matches(iter(rows), "取片", 10, diverse=True)
    assert result["matches"][:2] == rows[-2:]
    assert Counter(row["path"] for row in result["matches"])["Controllers/Legacy.cs"] == 4
    assert result["truncated"]
    legacy = select_matches(iter(rows), "取片", 10)
    assert legacy["matches"] == rows[:10] and legacy["truncated"]


def test_literal_path_request_precedes_generic_entry_hint_and_generated_code_remains_available():
    rows = [
        hit("Workflow/OtherTask.cs"),
        hit("Controls/Target.Designer.cs"),
        hit("Controls/Target.cs"),
    ]
    result = select_matches(iter(rows), "Target", 3, diverse=True)
    assert [row["path"] for row in result["matches"]] == [
        "Controls/Target.cs",
        "Controls/Target.Designer.cs",
        "Workflow/OtherTask.cs",
    ]
    assert not result["truncated"]


@pytest.mark.parametrize("limit", [1, 4, 10, 100])
def test_limit_is_honored_and_any_omitted_hits_are_reported(limit):
    rows = [hit(f"Tasks/Work{i}Task.cs", n) for i in range(8) for n in range(1, 9)]
    result = select_matches(iter(rows), "same", limit, diverse=True)
    assert len(result["matches"]) <= limit
    assert len({(row["path"], row["line"]) for row in result["matches"]}) == len(result["matches"])
    assert max(Counter(row["path"] for row in result["matches"]).values()) <= 4
    assert result["truncated"]


def test_empty_and_small_exact_match_sets_do_not_claim_truncation():
    assert select_matches(iter([]), "none", 10, diverse=True) == {"matches": [], "truncated": False}
    rows = [hit("b.cs"), hit("a.cs", 9)]
    result = select_matches(iter(rows), "code", 10, diverse=True)
    assert result == {"matches": [rows[1], rows[0]], "truncated": False}
