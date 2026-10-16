"""项目预算、持久结算与临时目录边界；数据库和文件均真实使用临时目录。"""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import pytest

from app.infrastructure.database.registry import Base
from app.infrastructure.database.session import Database
from app.modules.code_changes.policy import MEBIBYTE, WorkPolicy, profile_version


@pytest.fixture
def policy(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    database = Database(tmp_path / "budget.sqlite3")
    Base.metadata.create_all(database.engine)
    ledger = WorkPolicy(SimpleNamespace(scratch=scratch), database, "project-a")
    monkeypatch.setattr(WorkPolicy, "day", staticmethod(lambda: "2026-10-16"))
    ledger.save({"reading_token_limit": 1000, "min_free_mb": 0, "max_storage_mb": 100})
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
        ledger = WorkPolicy(policy.paths, restored, "project-a")
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


def test_windows_scratch_budget_defaults_persist_and_reject_unrealistic_small_layer(policy):
    from pydantic import ValidationError

    assert policy.get().windows_scratch_mb == 32768
    assert policy.limits()["windows_scratch_mb"] == 32768
    policy.save({"windows_scratch_mb": 65536})
    assert (
        WorkPolicy(policy.paths, policy.database, "project-a").limits()["windows_scratch_mb"]
        == 65536
    )
    for invalid in (1024, 20479, 1_048_577):
        with pytest.raises(ValidationError):
            policy.save({"windows_scratch_mb": invalid})
    assert policy.get().windows_scratch_mb == 65536


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
    other = WorkPolicy(policy.paths, policy.database, "project-b")
    with pytest.raises(ValueError, match="不属于当前项目"):
        other.settle(receipt, 1)
    assert other.tokens()["reserved_tokens"] == 0
    policy.settle({**receipt, "maximum": 1_000_000, "day": "2000-01-01"}, 100)
    assert policy.tokens()["reserved_tokens"] == 100


def test_late_settlement_updates_original_utc_day_not_new_day(policy, monkeypatch):
    receipt = policy.reserve(900)
    monkeypatch.setattr(WorkPolicy, "day", staticmethod(lambda: "2026-10-17"))
    policy.settle(receipt, 120)
    assert policy.tokens() == {
        "day": "2026-10-17",
        "reserved_tokens": 0,
        "actual_tokens": 0,
        "calls": 0,
    }
    policy.reserve(1000)
    monkeypatch.setattr(WorkPolicy, "day", staticmethod(lambda: "2026-10-16"))
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
    other = WorkPolicy(policy.paths, policy.database, "project-b")
    assert other.get().reading_token_limit == 500000
    other.save({"reading_token_limit": 2000})
    other.reserve(1500)
    assert policy.get().reading_token_limit == 1000
    assert policy.tokens()["reserved_tokens"] == 0
    assert other.tokens()["reserved_tokens"] == 1500


def test_unlimited_policy_persists_preserves_usage_and_can_restore_finite_limit(policy):
    first = policy.reserve(1000)
    before = policy.tokens()
    policy.save({**policy.get().model_dump(), "reading_token_limit": None})
    restored = WorkPolicy(policy.paths, policy.database, "project-a")
    assert restored.get().reading_token_limit is None
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
    other = WorkPolicy(policy.paths, policy.database, "project-b")
    assert other.get().reading_token_limit == 500000
    with pytest.raises(ValueError, match="预算不足"):
        other.reserve(500001)
    restored.save({**restored.get().model_dump(), "reading_token_limit": 1000})
    with pytest.raises(ValueError, match="预算不足"):
        restored.reserve(1)
    assert restored.tokens()["actual_tokens"] == 1_500_000
    assert restored.tokens()["calls"] == 2


def test_unlimited_parallel_reservations_still_accumulate_atomically(policy):
    policy.save({**policy.get().model_dump(), "reading_token_limit": None})
    with ThreadPoolExecutor(max_workers=8) as pool:
        receipts = list(pool.map(lambda _: policy.reserve(1_000_000), range(16)))
    assert len({receipt["id"] for receipt in receipts}) == 16
    assert policy.tokens()["reserved_tokens"] == 16_000_000
    assert policy.tokens()["calls"] == 16


@pytest.mark.parametrize("value", [-1, 0, 999, 100_000_001])
def test_finite_token_limit_validation_is_unchanged(policy, value):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        policy.save({"reading_token_limit": value})
    assert policy.get().reading_token_limit == 1000


def test_tokens_uses_one_day_snapshot_even_at_utc_rollover(policy, monkeypatch):
    policy.reserve(500)
    days = iter(["2026-10-16", "2026-10-17"])
    monkeypatch.setattr(WorkPolicy, "day", staticmethod(lambda: next(days)))
    report = policy.tokens()
    assert report["day"] == "2026-10-16" and report["reserved_tokens"] == 500


def _directory_link(link, target):
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            check=False,
        )
        if result.returncode:
            pytest.skip("当前 Windows 不能创建测试目录联接")
    else:
        link.symlink_to(target, target_is_directory=True)


@pytest.mark.parametrize("placement", ["scope", "parent", "child"])
def test_storage_rejects_directory_links_without_traversing_outside(policy, tmp_path, placement):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("untouched", encoding="utf-8")
    root = policy.paths.scratch / "project-a"
    if placement == "scope":
        _directory_link(root, outside)
    elif placement == "parent":
        _directory_link(root, outside)
        root = root / "nested"
    else:
        root.mkdir()
        _directory_link(root / "nested", outside)
    try:
        with pytest.raises(ValueError, match="链接"):
            policy.storage(root)
        assert (outside / "keep.txt").read_text(encoding="utf-8") == "untouched"
    finally:
        link = policy.paths.scratch / "project-a"
        if placement == "child":
            link = link / "nested"
        link.rmdir() if os.name == "nt" else link.unlink()


def test_storage_rejects_broken_root_directory_link(policy, tmp_path):
    link = policy.paths.scratch / "project-a"
    _directory_link(link, tmp_path / "does-not-exist")
    try:
        with pytest.raises(ValueError, match="链接"):
            policy.storage(link)
    finally:
        link.rmdir() if os.name == "nt" else link.unlink()


def test_storage_counts_real_files_and_case_insensitive_logs_and_rejects_outside(policy, tmp_path):
    root = policy.paths.scratch / "project-a"
    root.mkdir()
    (root / "output.LOG").write_bytes(b"a" * 10)
    (root / "module.cs").write_bytes(b"b" * 20)
    assert policy.storage(root) == {"storage_bytes": 30, "logs_bytes": 10}
    assert policy.storage(root / "not-yet-created")["storage_bytes"] == 0
    with pytest.raises(ValueError, match="临时目录"):
        policy.storage(tmp_path)


def test_storage_rejects_hardlinks(policy):
    root = policy.paths.scratch / "project-a"
    root.mkdir()
    (root / "original").write_bytes(b"keep")
    os.link(root / "original", root / "alias")
    with pytest.raises(ValueError, match="硬链接"):
        policy.storage(root)


def test_space_quota_and_free_disk_have_exact_inclusive_boundary(policy, monkeypatch):
    root = policy.paths.scratch / "project-a"
    root.mkdir()
    (root / "output").write_bytes(b"abcd")
    monkeypatch.setattr(
        "app.modules.code_changes.policy.shutil.disk_usage",
        lambda _: SimpleNamespace(free=200 * MEBIBYTE),
    )
    assert policy.check_space(root, 100 * MEBIBYTE - 4)["storage_bytes"] == 4
    with pytest.raises(ValueError, match="临时空间额度不足"):
        policy.check_space(root, 100 * MEBIBYTE - 3)
    policy.save({"reading_token_limit": 1000, "min_free_mb": 1})
    monkeypatch.setattr(
        "app.modules.code_changes.policy.shutil.disk_usage",
        lambda _: SimpleNamespace(free=MEBIBYTE + 5),
    )
    policy.check_space(root, 5)
    with pytest.raises(ValueError, match="剩余磁盘空间不足"):
        policy.check_space(root, 6)


def test_profile_version_invalidates_baseline_policy_changes():
    profile = {
        "argv": ["python", "-m", "pytest"],
        "executor": {"kind": "container"},
        "timeout_seconds": 120,
        "category": "test",
        "baseline_required": False,
    }
    assert profile_version(profile) != profile_version({**profile, "baseline_required": True})
    assert profile_version(profile) == profile_version({**profile, "name": "display change"})
