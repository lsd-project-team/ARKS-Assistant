"""领域规则不依赖 Web 或数据库，直接验证状态与来源版本约束。"""

import pytest

from app.modules.handover.domain.records import Record


def record(state="draft", kind="debug_issue", payload=None):
    return Record("record-1", kind, 3, state, payload or {})


def test_archive_and_restore_leave_original_snapshot_unchanged():
    original = record()
    assert original.review("archive", {}).state == "archived"
    assert original.review("restore", {}).state == "needs_review"
    assert original.state == "draft" and original.version == 3


@pytest.mark.parametrize("state", ["confirmed", "archived", "rejected"])
def test_confirm_rejects_non_reviewable_states(state):
    with pytest.raises(ValueError):
        record(state).review("confirm", {})


def test_rejected_source_is_not_accepted_as_current_evidence():
    source = {"state": "rejected", "version": 1}
    current = record(payload={"evidence": [{"record_id": "source-1", "version": 1}]})
    with pytest.raises(ValueError, match="关联内容已被拒绝"):
        current.review("confirm", {"source-1": source})


def test_confirm_pins_exact_current_source_version():
    current = record(payload={"evidence": [{"record_id": "source-1", "version": 1}]})
    with pytest.raises(ValueError, match="来源有新版本"):
        current.review("confirm", {"source-1": {"state": "confirmed", "version": 2}})
    outcome = current.review("confirm", {"source-1": {"state": "confirmed", "version": 1}})
    assert outcome.linked_versions == {"source-1": 1}


def test_version_conflict_is_detected_before_state_change():
    current = record()
    with pytest.raises(ValueError, match="记录已被更新"):
        current.assert_version(2)
    assert current.state == "draft" and current.version == 3


@pytest.mark.parametrize("kind", ["job", "task", "candidate"])
def test_special_records_cannot_be_rejected_in_common_review(kind):
    with pytest.raises(ValueError):
        record(kind=kind).review("reject", {})
