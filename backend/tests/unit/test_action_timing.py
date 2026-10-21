"""统计反例、协议约束及有界文件解析。"""

import copy
import io
import math
import zipfile

import pytest
from pydantic import ValidationError

from app.modules.action_timing.packages import read_package
from app.modules.action_timing.schemas import TimingPackage
from app.modules.action_timing.statistics import distribution, interval_union, summarize
from tests.helpers.action_timing import raw_package, timing_package, zip_package


def test_distribution_nearest_rank_and_empty_are_not_zero():
    assert distribution([]) == {
        key: None for key in ("mean_ms", "min_ms", "max_ms", "p50_ms", "p95_ms")
    }
    assert distribution([30, 10]) == {
        "mean_ms": 20,
        "min_ms": 10,
        "max_ms": 30,
        "p50_ms": 10,
        "p95_ms": 30,
    }
    assert distribution(range(1, 101))["p95_ms"] == 95


def test_only_complete_successes_count_and_children_are_not_double_counted():
    package = timing_package()
    package["events"][1]["status"] = "skipped"
    package["events"][2]["status"] = "retry"
    package["events"][3]["status"] = "noop"
    package["events"][4]["status"] = "failed"
    result = summarize(package)
    assert result["action_count"] == 5 and result["stage_count"] == 1
    assert result["covered_actions"] == 1
    assert result["rows"][0]["valid_count"] == 1
    assert result["rows"][0]["mean_ms"] == 10
    assert all(row["mean_ms"] is None for row in result["rows"][1:])
    assert result["rows"][0]["stages"][0]["mean_ms"] == 7
    assert (
        interval_union(
            [
                {"start_ms": 0, "end_ms": 10},
                {"start_ms": 5, "end_ms": 15},
                {"start_ms": 3, "end_ms": 7},
            ]
        )
        == 15
    )


@pytest.mark.parametrize("reason", ["dropped", "unfinished", "state"])
def test_incomplete_run_retains_records_without_success_distribution(reason):
    package = timing_package()
    if reason == "dropped":
        package["manifest"]["dropped_events"] = 1
    elif reason == "unfinished":
        package["events"][1].update(status="incomplete", end_ms=None)
    else:
        package["manifest"]["state"] = "incomplete"
    result = summarize(package)
    assert not result["data_complete"]
    assert result["action_count"] == 5
    assert all(row["valid_count"] == 0 and row["mean_ms"] is None for row in result["rows"])


@pytest.mark.parametrize("value", [-1, math.nan, math.inf, True, "10"])
def test_invalid_start_time_is_rejected(value):
    package = timing_package()
    package["events"][0]["start_ms"] = value
    with pytest.raises(ValidationError):
        TimingPackage.model_validate(package)


@pytest.mark.parametrize(
    "case",
    [
        "unknown_action",
        "wrong_station",
        "negative_duration",
        "orphan",
        "cycle",
        "outside_parent",
        "async_child",
        "duplicate",
        "count",
        "owner",
        "open_run",
        "no_end",
    ],
)
def test_protocol_rejects_malformed_graph_and_untrusted_ownership(case):
    package = timing_package()
    if case == "unknown_action":
        package["events"][0]["action_code"] = "other"
    elif case == "wrong_station":
        package["events"][0]["station"] = "S2"
    elif case == "negative_duration":
        package["events"][0]["end_ms"] = -1
    elif case == "orphan":
        package["events"][-1]["parent_id"] = "missing"
    elif case == "cycle":
        package["events"][-1]["parent_id"] = "stage-0"
    elif case == "outside_parent":
        package["events"][-1]["end_ms"] = 11
    elif case == "async_child":
        package["events"][-1]["thread_id"] = 99
    elif case == "duplicate":
        package["events"][-1]["event_id"] = "event-0"
    elif case == "count":
        package["manifest"]["event_count"] = 0
    elif case == "owner":
        package["manifest"]["owner_id"] = "another-account"
    elif case == "open_run":
        package["manifest"]["state"] = "running"
    elif case == "no_end":
        package["events"][0]["end_ms"] = None
    with pytest.raises(ValidationError):
        TimingPackage.model_validate(package)


def test_branches_stay_separate_and_sample_statuses_are_counted():
    package = timing_package()
    extra = copy.deepcopy(package["events"][0])
    extra.update(
        event_id="extra",
        logical_id="other-logical",
        branch="drycycle.other",
        start_ms=100,
        end_ms=130,
    )
    package["events"].append(extra)
    result = summarize(package)
    branches = {item["branch"]: item for item in result["rows"][0]["branches"]}
    assert branches["drycycle.collector_test"]["mean_ms"] == 10
    assert branches["drycycle.other"]["mean_ms"] == 30
    assert result["rows"][0]["mean_ms"] is None


def test_stages_from_failed_parent_are_retained_but_not_success_samples():
    package = timing_package()
    package["events"][0]["status"] = "failed"
    stage = summarize(package)["rows"][0]["stages"][0]
    assert stage["count"] == 1 and stage["valid_count"] == 0
    assert stage["mean_ms"] is None


def test_zip_and_json_parse_to_same_protocol():
    assert read_package(zip_package()) == read_package(raw_package())
    with pytest.raises(ValueError, match="重复"):
        read_package(b'{"manifest":{},"manifest":{}}')
    with pytest.raises(ValueError):
        read_package(b"PKbroken")
    with pytest.raises(ValueError):
        read_package(b"\xff")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("../manifest.json", "{}")
        archive.writestr("events.jsonl", "")
    with pytest.raises(ValueError, match="ZIP"):
        read_package(output.getvalue())


def test_zip_expanded_size_is_bounded(monkeypatch):
    from app.modules.action_timing import packages

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("events.jsonl", "0" * 5000)
    assert len(output.getvalue()) < 1024
    monkeypatch.setattr(packages, "MAX_BYTES", 1024)
    with pytest.raises(ValueError, match="ZIP"):
        packages.read_package(output.getvalue())
