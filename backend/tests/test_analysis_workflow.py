from types import SimpleNamespace

from langchain_core.messages import ToolMessage

from app.analysis_policy import analysis_policy, configured_analysis
from app.analysis_progress import AnalysisProgress
from app.config import AnalysisSettings, AppSettings
from app.retrieval_budget import RetrievalBudget
from app.run_completion import completion_report
from app.source_evidence import SourceEvidence, source_excerpt
from app.source_reads import batch_source


def test_scope_policy_preserves_configuration_and_continuation_scope():
    settings = AppSettings()
    effective, policy = configured_analysis(settings, "这个项目还有没完成的进度到哪里了")
    assert policy["mode"] == "deep" and policy["limit"] == 64 and policy["reserve"] == 8
    assert effective.model.output_tokens == 8192 and settings.model.output_tokens == 4096
    assert analysis_policy(settings, "继续核查", policy)["mode"] == "deep"
    assert analysis_policy(settings, "解释这个函数")["mode"] == "standard"
    assert analysis_policy(settings, "另一个普通问题", policy)["continuing"] is False


def test_batch_merges_ranges_and_records_only_returned_content(services):
    workspace = services[2]
    (workspace.root / "Long.cs").write_text("\n".join(f"// {i}" for i in range(2000)))
    evidence = SourceEvidence(workspace, lambda *_: None)
    result = batch_source(
        workspace,
        [
            {"path": "Program.cs", "start_line": 1, "end_line": 2},
            {"path": "/workspace/Program.cs", "start_line": 2, "end_line": 3},
            {"path": "Missing.cs", "start_line": 1, "end_line": 3},
        ],
        evidence,
    )
    assert len(result["reads"]) == 1 and len(result["errors"]) == 1
    assert len(evidence.reads) == 1 and evidence.covered("Program.cs", 1, 3)
    result = batch_source(
        workspace,
        [
            {"path": "Long.cs", "start_line": start, "end_line": start + 499}
            for start in (1, 501, 1001)
        ],
        evidence,
    )
    returned = sum(len(row["lines"]) for row in result["reads"])
    assert 0 < returned <= 1200
    assert all(
        not evidence.covered(row["path"], row["start_line"], row["end_line"])
        for row in result["remaining"]
    )
    assert result["remaining"] and not evidence.covered("Long.cs", 1001, 1500)


async def test_reserve_budget_and_same_version_cached_reads_are_distinct(services):
    workspace = services[2]
    events = []
    evidence = SourceEvidence(workspace, lambda *_: None)
    progress = AnalysisProgress(evidence, lambda *_: None)
    budget = RetrievalBudget(lambda *event: events.append(event), 3, 1, evidence, progress)

    async def handler(request):
        if request.tool_call["name"] == "read_source":
            evidence.record(source_excerpt(workspace, **request.tool_call["args"]))
        return ToolMessage(content="已读取", tool_call_id=request.tool_call["id"])

    async def call(name, arguments=None):
        return await budget.awrap_tool_call(
            SimpleNamespace(
                tool_call={
                    "id": str(budget.counts["attempted"]),
                    "name": name,
                    "args": arguments or {},
                }
            ),
            handler,
        )

    await call("search_source")
    await call("search_source")
    skipped = await call("search_source")
    assert skipped.additional_kwargs["skip_reason"] == "verification_reserved"
    await call("read_source", {"path": "Program.cs", "start_line": 1, "end_line": 3})
    cached = await call("read_source", {"path": "Program.cs", "start_line": 1, "end_line": 3})
    assert cached.additional_kwargs["cached"] and budget.used == 3
    await call("read_source", {"path": "Missing.cs", "start_line": 1, "end_line": 2})
    assert budget.counts == {"attempted": 6, "success": 4, "skipped": 2, "failed": 0, "cached": 1}
    assert progress.snapshot()["pending"][0]["path"] == "Missing.cs"
    assert any(payload["exhausted"] is False for kind, payload in events)


def test_continuation_reuses_matching_evidence_and_invalidates_changed_file(services):
    workspace = services[2]
    evidence = SourceEvidence(workspace, lambda *_: None)
    old = AnalysisProgress(evidence, lambda *_: None)
    old.plan([{"path": "Program.cs", "start_line": 1, "end_line": 3}])
    evidence.record(source_excerpt(workspace, "Program.cs", 1, 3))
    previous = old.snapshot()
    fresh = AnalysisProgress(SourceEvidence(workspace, lambda *_: None), lambda *_: None, previous)
    assert "previous_analysis" in fresh.reuse(previous)
    assert not fresh.snapshot()["pending"]
    (workspace.root / "Program.cs").write_text("// modified\nclass Program {}")
    changed = AnalysisProgress(
        SourceEvidence(workspace, lambda *_: None), lambda *_: None, previous
    )
    changed.reuse(previous)
    assert not changed.evidence.reads and changed.snapshot()["pending"]
    assert not changed.evidence.covered("Program.cs", 100, 200)


def test_partial_review_and_output_cutoff_have_independent_status():
    progress = {"pending": [{"path": "Missing.cs"}], "checks": [1]}
    counts = {"skipped": 1, "failed": 0}
    report = completion_report({"output": "complete"}, progress, counts)
    assert report["stage"] == "partial_review" and report["coverage"] == "partial"
    assert (
        completion_report({"output": "incomplete"}, progress, counts)["stage"]
        == "answer_incomplete"
    )
    assert AnalysisSettings().max_continuations == 2


def test_missing_parent_directory_is_resolved_only_for_unique_source(services):
    workspace = services[2]
    folder = workspace.root / "Module"
    folder.mkdir()
    (folder / "Nested.cs").write_text("class Nested {}")
    evidence = SourceEvidence(workspace, lambda *_: None)
    progress = AnalysisProgress(evidence, lambda *_: None)
    progress.plan([{"path": "Nested.cs", "start_line": 1, "end_line": 1}])
    result = batch_source(
        workspace, [{"path": "Nested.cs", "start_line": 1, "end_line": 1}], evidence
    )
    assert result["reads"][0]["path"] == "Module/Nested.cs"
    assert not progress.snapshot()["pending"]
    (workspace.root / "Other").mkdir()
    (workspace.root / "Other" / "Nested.cs").write_text("class Different {}")
    assert not evidence.covered("Nested.cs", 1, 1)
    assert batch_source(
        workspace, [{"path": "Nested.cs", "start_line": 1, "end_line": 1}], evidence
    )["errors"]
