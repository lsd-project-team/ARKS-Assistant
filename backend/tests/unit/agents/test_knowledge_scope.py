import pytest

from app.agents.runtime.knowledge_scope import (
    pieces,
    scope_problems,
    scoped_fallback,
    selected_records,
    selection_input,
    selection_result,
)

BEFORE, TARGET, AFTER = "7月23日，3μm。", "7月25日，23.2℃，精度-4~2μm。", "7月27日，900μm。"
REF = "[跨日记录 · v4](debug-issue:trial/4)"
ROWS = [{"reference": REF, "content": {"正文": BEFORE + TARGET + AFTER}}]


def choice(start=2, end=2, index=1, field="正文"):
    return {"selections": [{"id": index, "parts": [{"field": field, "start": start, "end": end}]}]}


def test_span_selection_returns_immutable_original_not_model_copied_values():
    projected = selection_input(ROWS)
    assert projected[0]["id"] == 1
    assert projected[0]["content"]["正文"][1] == {"number": 2, "text": TARGET}
    selected = selected_records(choice(), ROWS)
    assert selected == [{"reference": REF, "content": {"正文": TARGET}}]
    assert ROWS[0]["content"]["正文"] == BEFORE + TARGET + AFTER
    assert BEFORE not in scoped_fallback(selected) and AFTER not in scoped_fallback(selected)


@pytest.mark.parametrize(
    "result",
    [
        {},
        {"selections": "all"},
        choice(0, 1),
        choice(3, 2),
        choice(1, 4),
        choice(index=2),
        choice(index=True),
        choice(start=True),
        choice(field="unknown"),
        {"selections": [{"id": 1, "parts": []}]},
    ],
)
def test_unknown_or_invalid_locations_are_rejected(result):
    with pytest.raises((ValueError, KeyError, TypeError)):
        selected_records(result, ROWS)


def test_full_source_including_newlines_is_restored_exactly_and_overlaps_deduplicated():
    original = "【问题】\n0.6×0.45mm。\n\n【方案】\n高度280~300\n"
    rows = [{"reference": REF, "content": {"正文": original}}]
    assert "".join(pieces(original)) == original
    data = choice(1, len(pieces(original)))
    data["selections"][0]["parts"].append({"field": "正文", "start": 2, "end": 2})
    assert selected_records(data, rows)[0]["content"]["正文"] == original


def test_duplicate_record_ids_rejected_without_mutating_snapshot():
    data = choice()
    data["selections"].append(data["selections"][0])
    with pytest.raises(ValueError):
        selected_records(data, ROWS)


def test_scope_checks_versions_images_and_protects_code_literals():
    selected = selected_records(choice(), ROWS)
    assert scope_problems("结果", "[旧版](debug-issue:trial/3)", selected)
    assert scope_problems("全部原图", TARGET, selected)
    assert not scope_problems("全部原图", TARGET + REF, selected)
    assert not scope_problems("代码", "```\ndebug-issue:other/1\n```", selected)


def test_selection_redacts_secrets_without_modifying_original():
    rows = [{"reference": REF, "content": {"正文": "api_key='do-not-leak'\n" + TARGET}}]
    projected = selection_input(rows)
    assert "do-not-leak" not in str(projected)
    assert "do-not-leak" not in scoped_fallback(selected_records(choice(1, 2), rows))
    assert "do-not-leak" in rows[0]["content"]["正文"]


@pytest.mark.parametrize("result", [{"selections": []}, {"scope": "records", "selections": []}])
def test_record_query_with_no_matches_stays_in_records_scope(result):
    assert selection_result(result, ROWS) == ("records", [])


def test_general_question_scope_is_distinct_from_empty_record_selection():
    assert selection_result({"scope": "general", "selections": []}, ROWS) == ("general", [])


@pytest.mark.parametrize("scope", [None, True, [], "unrecognized"])
def test_invalid_question_scope_is_rejected(scope):
    with pytest.raises(ValueError):
        selection_result({"scope": scope, "selections": []}, ROWS)


def test_general_scope_cannot_select_and_publish_historical_facts():
    with pytest.raises(ValueError, match="general question"):
        selection_result({**choice(), "scope": "general"}, ROWS)
