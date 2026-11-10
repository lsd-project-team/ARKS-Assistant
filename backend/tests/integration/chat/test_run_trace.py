"""运行概况以可见事件为准，缓存、失败、未知耗时不能伪装成实际调用或零值。"""

import pytest

from app.agents.runtime.engine import AgentRuntime
from app.modules.chat.context import ConversationContext
from app.modules.chat.run_trace import RunTrace, elapsed_ms


def test_trace_distinguishes_cache_failure_unknown_timing_and_parallel_intervals():
    trace = RunTrace()

    def emit(kind, payload, at="2026-10-30T00:00:00+00:00"):
        trace.observe({"kind": kind, "payload": payload, "created_at": at})

    emit("context_sources", {"tracking_version": 1})
    emit(
        "history_selection",
        {"status": "selected", "candidate_count": 8, "selected_count": 3, "duration_ms": 120},
    )
    emit(
        "history_selection",
        {
            "status": "selected",
            "candidate_count": 8,
            "selected_count": 3,
            "cached": True,
            "duration_ms": 0,
        },
    )
    emit(
        "knowledge_filter",
        {"status": "unavailable", "candidate_count": 2, "selected_count": 0, "duration_ms": 30},
    )
    emit("provider_usage", {"purpose": "answer", "duration_ms": 200})
    emit("provider_usage", {"purpose": "answer", "status": "failed", "duration_ms": 100})
    emit("provider_usage", {"purpose": "summary"})
    emit("tool_start", {"id": "read", "name": "read_source"})
    emit("tool_start", {"id": "other", "name": "read_source"})
    emit("tool_end", {"id": "read", "status": "success"}, "2026-10-30T00:00:00.300+00:00")
    emit("knowledge_answer_review", {"verdict": "unknown", "reason": "核查未完成"})
    report = trace.report(
        {
            "status": "completed",
            "started_at": "2026-10-30T00:00:00+00:00",
            "finished_at": "2026-10-30T00:00:00.400+00:00",
        }
    )
    assert report["elapsed_ms"] == 400 and report["model_calls"] == 3
    assert report["filters"]["history"]["passes"] == 1
    assert report["filters"]["history"]["cache_hits"] == 1
    assert report["filters"]["history"]["duration_ms"] == 120
    assert report["requests"][0] == {
        "purpose": "answer",
        "calls": 2,
        "timed_calls": 2,
        "duration_ms": 300,
        "failed_calls": 1,
    }
    assert report["requests"][1]["timed_calls"] == 0
    assert report["tools"][0]["duration_ms"] == 300
    assert "duration_ms" not in report["tools"][1]
    assert report["checks"]["knowledge_answer_review"]["verdict"] == "unknown"


@pytest.mark.parametrize(
    "start,end", [(None, None), ("bad", "bad"), ("2026-10-30T00:00:01Z", "2026-10-30T00:00:00Z")]
)
def test_missing_or_invalid_timestamps_are_unknown(start, end):
    assert elapsed_ms(start, end) is None


def test_run_context_projects_real_events_without_changing_archive(services):
    paths, _, workspace, repository, memories, settings = services
    run = repository.create_run(None, "查询资料", [])
    repository.event(run["id"], "context_sources", {"tracking_version": 1, "memories": []})
    repository.event(
        run["id"],
        "memory_selection",
        {"status": "none", "candidate_count": 0, "selected_count": 0, "duration_ms": 2},
    )
    repository.event(
        run["id"],
        "knowledge_filter",
        {"status": "selected", "candidate_count": 6, "selected_count": 2, "duration_ms": 10},
    )
    repository.event(
        run["id"],
        "provider_usage",
        {"purpose": "knowledge_selection", "duration_ms": 8, "reported": False},
    )
    repository.event(run["id"], "knowledge_answer_review", {"verdict": "passed"})
    repository.finish(run["id"], "回答档案")
    before = repository.thread(run["thread_id"])
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    try:
        result = ConversationContext(runtime).run_sources(run["id"])
        assert result["trace"]["recorded"] is True
        assert result["trace"]["filters"]["knowledge"]["selected_count"] == 2
        assert result["trace"]["filters"]["memory"]["candidate_count"] == 0
        assert result["trace"]["model_calls"] == 1
        assert repository.thread(run["thread_id"]) == before
    finally:
        runtime.semantic.close()
