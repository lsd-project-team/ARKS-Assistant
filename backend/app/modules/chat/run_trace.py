"""从已记录且已按账号过滤的事件生成运行概况，不推测内部思考或缺失耗时。"""

from datetime import UTC, datetime


def elapsed_ms(start, end):
    if not start or not end:
        return None
    try:
        value = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
        return round(value * 1000) if value >= 0 else None
    except (ValueError, TypeError):
        return None


class RunTrace:
    def __init__(self):
        self.filters, self.checks, self.requests, self.tools = {}, {}, {}, {}
        self.tracked = False

    def observe(self, event):
        kind, row = event["kind"], event["payload"]
        if kind == "context_sources":
            self.tracked = bool(row.get("tracking_version"))
        key = {
            "memory_selection": "memory",
            "history_selection": "history",
            "knowledge_filter": "knowledge",
        }.get(kind)
        if key:
            previous = self.filters.get(key, {})
            durations = [
                value
                for value in (previous.get("duration_ms"), row.get("duration_ms"))
                if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0
            ]
            self.filters[key] = {
                **row,
                "duration_ms": sum(durations) if durations else None,
                "passes": previous.get("passes", 0) + (not row.get("cached", False)),
                "cache_hits": previous.get("cache_hits", 0) + bool(row.get("cached")),
            }
        if kind == "provider_usage":
            purpose = row.get("purpose", "unknown")
            item = self.requests.setdefault(
                purpose,
                {
                    "purpose": purpose,
                    "calls": 0,
                    "timed_calls": 0,
                    "duration_ms": 0,
                    "failed_calls": 0,
                },
            )
            item["calls"] += 1
            item["failed_calls"] += row.get("status") == "failed"
            duration = row.get("duration_ms")
            if (
                isinstance(duration, (int, float))
                and not isinstance(duration, bool)
                and duration >= 0
            ):
                item["duration_ms"] += duration
                item["timed_calls"] += 1
        if kind in {"answer_validation", "source_review", "knowledge_answer_review"}:
            self.checks[kind] = row
        if kind == "tool_start":
            self.tools[row["id"]] = {
                "id": row["id"],
                "name": row["name"],
                "started_at": event["created_at"],
            }
        if kind == "tool_end":
            item = self.tools.get(row["id"])
            if item:
                item.update(
                    status=row.get("status", "success"),
                    duration_ms=elapsed_ms(item["started_at"], event["created_at"]),
                )

    def report(self, run):
        end = run.get("finished_at")
        if not end and run["status"] in {"running", "cancelling"}:
            end = datetime.now(UTC).isoformat()
        return {
            "recorded": self.tracked,
            "status": run["status"],
            "elapsed_ms": elapsed_ms(run.get("started_at"), end),
            "queue_ms": elapsed_ms(run.get("created_at"), run.get("started_at")),
            "model_calls": sum(row["calls"] for row in self.requests.values()),
            "filters": self.filters,
            "checks": self.checks,
            "requests": list(self.requests.values()),
            "tools": [
                {key: value for key, value in row.items() if key != "started_at"}
                for row in self.tools.values()
            ],
        }
