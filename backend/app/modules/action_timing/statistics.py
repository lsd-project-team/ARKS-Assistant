"""仅完整成功调用参与分布；父子和并发区间不相加成节拍。"""

import math
from collections import Counter, defaultdict

from app.modules.action_timing.catalog import CATALOG


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        return {key: None for key in ("mean_ms", "min_ms", "max_ms", "p50_ms", "p95_ms")}
    return {
        "mean_ms": sum(ordered) / len(ordered),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "p50_ms": ordered[math.ceil(len(ordered) * 0.5) - 1],
        "p95_ms": ordered[math.ceil(len(ordered) * 0.95) - 1],
    }


def metrics(events, complete, parent_success=None):
    counts = Counter(event["status"] for event in events)
    values = [
        event["end_ms"] - event["start_ms"]
        for event in events
        if complete
        and event["status"] == "success"
        and event["end_ms"] is not None
        and (parent_success is None or event["parent_id"] in parent_success)
    ]
    return {
        "count": len(events),
        "valid_count": len(values),
        "statuses": dict(counts),
        **distribution(values),
    }


def interval_union(events):
    intervals = sorted(
        (event["start_ms"], event["end_ms"]) for event in events if event["end_ms"] is not None
    )
    total, previous_end = 0.0, 0.0
    for start, end in intervals:
        total += max(0, end - max(start, previous_end))
        previous_end = max(previous_end, end)
    return total


def summarize(package):
    events = package["events"]
    manifest = package["manifest"]
    complete = (
        manifest["state"] != "incomplete"
        and manifest["dropped_events"] == 0
        and all(event["status"] != "incomplete" for event in events)
    )
    actions = [event for event in events if event["kind"] == "action"]
    parent_success = {event["event_id"] for event in actions if event["status"] == "success"}
    rows = []
    for definition in CATALOG:
        own = [event for event in actions if event["action_code"] == definition["code"]]
        branches, stages = defaultdict(list), defaultdict(list)
        for event in own:
            branches[event["branch"]].append(event)
        for event in events:
            if event["kind"] == "stage" and event["action_code"] == definition["code"]:
                stages[(event["branch"], event["stage"], event["category"])].append(event)
        rows.append(
            {
                **definition,
                **metrics(own, complete),
                **(distribution([]) if len(branches) > 1 else {}),
                "branches": [
                    {"branch": branch, **metrics(items, complete)}
                    for branch, items in sorted(branches.items())
                ],
                "stages": [
                    {
                        "branch": branch,
                        "stage": stage,
                        "category": category,
                        **metrics(items, complete, parent_success),
                    }
                    for (branch, stage, category), items in sorted(stages.items())
                ],
            }
        )
    return {
        "aggregation_version": "1-nearest-rank",
        "data_complete": complete,
        "source_kind": manifest["source_kind"],
        "action_count": len(actions),
        "stage_count": len(events) - len(actions),
        "covered_actions": sum(row["valid_count"] > 0 for row in rows),
        "statuses": dict(Counter(event["status"] for event in actions)),
        "active_union_ms": interval_union(actions),
        "rows": rows,
    }
