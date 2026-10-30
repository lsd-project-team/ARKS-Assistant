"""聊天模型预算与持久结算；数据库和文件均真实使用临时目录。"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from app.infrastructure.database.registry import Base
from app.infrastructure.database.session import Database
from app.modules.settings.model_ledger import ModelLedger


@pytest.fixture
def policy(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    database = Database(tmp_path / "budget.sqlite3")
    Base.metadata.create_all(database.engine)
    ledger = ModelLedger(database, "project-a")
    monkeypatch.setattr(ModelLedger, "day", staticmethod(lambda: "2026-10-16"))
    ledger.save({"token_limit": 1000})
    yield ledger
    database.close()


def test_quota_persists_across_service_and_database_restart(policy):
    receipt = policy.reserve(1000)
    with pytest.raises(ValueError, match="预算不足"):
        policy.reserve(1)
    path = Path(policy.database.engine.url.database)
    policy.database.close()
    restored = Database(path)
    try:
        ledger = ModelLedger(restored, "project-a")
        assert ledger.tokens() == {
            "day": "2026-10-16",
            "reserved_tokens": 1000,
            "actual_tokens": 0,
            "calls": 1,
        }
        ledger.settle(receipt, 250)
        ledger.settle(receipt, 0)
        assert ledger.tokens()["reserved_tokens"] == 250
        assert ledger.tokens()["actual_tokens"] == 250
        assert ledger.reserve(750)["maximum"] == 750
    finally:
        restored.close()


def test_parallel_reservations_never_overspend_and_failed_claims_roll_back(policy):
    barrier = Barrier(12)

    def reserve():
        barrier.wait()
        try:
            return policy.reserve(150)
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=12) as pool:
        receipts = list(pool.map(lambda _: reserve(), range(12)))
    assert sum(receipt is not None for receipt in receipts) == 6
    assert policy.tokens()["reserved_tokens"] == 900
    assert policy.tokens()["calls"] == 6


def test_parallel_duplicate_settlement_refunds_only_once(policy):
    receipt = policy.reserve(900)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: policy.settle(receipt, 125), range(16)))
    assert policy.tokens()["reserved_tokens"] == 125
    assert policy.tokens()["actual_tokens"] == 125
    assert policy.tokens()["calls"] == 1


def test_unknown_usage_holds_budget_and_forged_receipt_cannot_refund_other_project(policy):
    receipt = policy.reserve(900)
    policy.settle(receipt, None)
    assert policy.tokens()["reserved_tokens"] == 900
    other = ModelLedger(policy.database, "project-b")
    with pytest.raises(ValueError, match="不属于当前项目"):
        other.settle(receipt, 1)
    assert other.tokens()["reserved_tokens"] == 0
    policy.settle({**receipt, "maximum": 1_000_000, "day": "2000-01-01"}, 100)
    assert policy.tokens()["reserved_tokens"] == 100


def test_late_settlement_updates_original_utc_day_not_new_day(policy, monkeypatch):
    receipt = policy.reserve(900)
    monkeypatch.setattr(ModelLedger, "day", staticmethod(lambda: "2026-10-17"))
    policy.settle(receipt, 120)
    assert policy.tokens() == {
        "day": "2026-10-17",
        "reserved_tokens": 0,
        "actual_tokens": 0,
        "calls": 0,
    }
    policy.reserve(1000)
    monkeypatch.setattr(ModelLedger, "day", staticmethod(lambda: "2026-10-16"))
    assert policy.tokens()["actual_tokens"] == 120
    assert policy.tokens()["reserved_tokens"] == 120


def test_actual_usage_over_reservation_is_recorded_as_debt(policy):
    receipt = policy.reserve(200)
    policy.settle(receipt, 1200)
    assert policy.tokens()["reserved_tokens"] == 1200
    assert policy.tokens()["actual_tokens"] == 1200
    with pytest.raises(ValueError, match="预算不足"):
        policy.reserve(1)


@pytest.mark.parametrize("value", [None, 0, -1, True, 1.5, "10"])
def test_reservation_rejects_non_positive_or_non_integer_amount(policy, value):
    with pytest.raises(ValueError, match="正整数"):
        policy.reserve(value)
    assert policy.tokens()["calls"] == 0


@pytest.mark.parametrize("value", [-1, True, 1.5, "10"])
def test_settlement_rejects_invalid_amount_without_refunding(policy, value):
    receipt = policy.reserve(900)
    with pytest.raises(ValueError, match="非负整数"):
        policy.settle(receipt, value)
    assert policy.tokens()["reserved_tokens"] == 900


def test_policy_and_usage_are_project_scoped(policy):
    other = ModelLedger(policy.database, "project-b")
    assert other.get().token_limit == 500000
    other.save({"token_limit": 2000})
    other.reserve(1500)
    assert policy.get().token_limit == 1000
    assert policy.tokens()["reserved_tokens"] == 0
    assert other.tokens()["reserved_tokens"] == 1500


def test_unlimited_policy_persists_preserves_usage_and_can_restore_finite_limit(policy):
    first = policy.reserve(1000)
    before = policy.tokens()
    policy.save({**policy.get().model_dump(), "token_limit": None})
    restored = ModelLedger(policy.database, "project-a")
    assert restored.get().token_limit is None
    assert restored.tokens() == before
    second = restored.reserve(2_000_000)
    restored.settle(second, 1_500_000)
    restored.settle(second, 0)
    restored.settle(first, None)
    assert restored.tokens() == {
        "day": "2026-10-16",
        "reserved_tokens": 1_501_000,
        "actual_tokens": 1_500_000,
        "calls": 2,
    }
    other = ModelLedger(policy.database, "project-b")
    assert other.get().token_limit == 500000
    with pytest.raises(ValueError, match="预算不足"):
        other.reserve(500001)
    restored.save({**restored.get().model_dump(), "token_limit": 1000})
    with pytest.raises(ValueError, match="预算不足"):
        restored.reserve(1)
    assert restored.tokens()["actual_tokens"] == 1_500_000
    assert restored.tokens()["calls"] == 2


def test_unlimited_parallel_reservations_still_accumulate_atomically(policy):
    policy.save({**policy.get().model_dump(), "token_limit": None})
    with ThreadPoolExecutor(max_workers=8) as pool:
        receipts = list(pool.map(lambda _: policy.reserve(1_000_000), range(16)))
    assert len({receipt["id"] for receipt in receipts}) == 16
    assert policy.tokens()["reserved_tokens"] == 16_000_000
    assert policy.tokens()["calls"] == 16


@pytest.mark.parametrize("value", [-1, 0, 999, 100_000_001])
def test_finite_token_limit_validation_is_unchanged(policy, value):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        policy.save({"token_limit": value})
    assert policy.get().token_limit == 1000


def test_tokens_uses_one_day_snapshot_even_at_utc_rollover(policy, monkeypatch):
    policy.reserve(500)
    days = iter(["2026-10-16", "2026-10-17"])
    monkeypatch.setattr(ModelLedger, "day", staticmethod(lambda: next(days)))
    report = policy.tokens()
    assert report["day"] == "2026-10-16" and report["reserved_tokens"] == 500
