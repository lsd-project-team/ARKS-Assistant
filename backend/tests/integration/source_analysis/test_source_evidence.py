"""验证源码证据边界与真实 Agent 工具循环，不把引用核对当成语义核对。"""

import json
import os

from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.context.tokens import estimate_tokens
from app.agents.runtime.engine import AgentRuntime
from app.agents.tools.source import source_tools
from app.core.config import AppSettings, ModelSettings, dump_json
from app.infrastructure.cache.versions import VersionCache
from app.infrastructure.providers.usage import reported_usage
from app.modules.source_analysis.evidence import (
    SourceEvidence,
    SourceEvidenceGuard,
    deduplicate_source_results,
    enclosing_excerpt,
    source_excerpt,
)
from tests.helpers.models import DeterministicModel


def test_citations_require_current_version_and_actual_range(services):
    _, _, workspace, *_ = services
    ledger = SourceEvidence(workspace, lambda *_args: None, required=True)
    ledger.record(source_excerpt(workspace, "Program.cs", 2, 2))
    assert ledger.check("入口 [Program.cs:2](source:Program.cs#L2)")["passed"]
    assert not ledger.check("[1-2](source:Program.cs#L1-L2)")["passed"]
    assert not ledger.check("[超界](source:Program.cs#L999)")["passed"]
    assert not ledger.check("[越界](source:../private.cs#L1)")["passed"]
    assert not ledger.check("[绝对](source:C:/secret.cs#L1)")["passed"]
    (workspace.root / "Program.cs").write_text("class Other {\n static void Main() {}\n}\n")
    report = ledger.check("[2](source:Program.cs#L2)")
    assert not report["passed"] and "文件发生变化" in report["reasons"][0]


async def test_selection_context_reads_current_method_and_respects_budget(services):
    _, _, workspace, *_ = services
    events = []
    ledger = SourceEvidence(workspace, lambda *event: events.append(event), required=True)
    excerpt = enclosing_excerpt(workspace, "Program.cs", 2)
    assert excerpt["symbol"]["name"] == "Main" and excerpt["complete_symbol"]
    selection = {"path": "Program.cs", "start_line": 2, "end_line": 2, "version": "a" * 64}
    context = await ledger.prepare([selection])
    assert workspace.read("Program.cs")["version"] in context
    assert ledger.check("[入口](source:Program.cs#L2)")["passed"]
    empty = SourceEvidence(workspace, lambda *event: events.append(event))
    assert not await empty.prepare([selection], max_tokens=1)
    assert not empty.reads and events[-1][0] == "source_context_skipped"


async def test_failed_tool_does_not_create_evidence(services):
    _, _, workspace, *_ = services
    ledger = SourceEvidence(workspace, lambda *_args: None)
    tools = {item.name: item for item in source_tools(workspace, ledger)}
    failure = await tools["read_source"].ainvoke({"path": "Missing.cs"})
    assert "源码工具未完成" in failure
    assert not ledger.reads
    payload = json.loads(
        await tools["read_source_context"].ainvoke({"path": "/workspace/Program.cs", "line": 2})
    )
    assert payload["symbol"]["name"] == "Main" and ledger.reads
    for path in ["../private.cs", "C:/secret.cs", "/elsewhere/Program.cs"]:
        failure = await tools["read_source"].ainvoke({"path": path})
        assert "源码工具未完成" in failure
    assert len(ledger.reads) == 1


async def test_guard_repairs_and_marks_unverified_links(services):
    _, _, workspace, *_ = services
    events = []
    ledger = SourceEvidence(workspace, lambda *event: events.append(event), required=True)
    guard = SourceEvidenceGuard(ledger)
    requests = []

    async def handler(request):
        requests.append(request)
        return ModelResponse(result=[AIMessage(content="结论 [坏引用](source:Program.cs#L999)")])

    request = ModelRequest(model=DeterministicModel(), messages=[HumanMessage(content="解释源码")])
    response = await guard.awrap_model_call(request, handler)
    assert len(requests) == 3 and "read_source" in requests[-1].messages[-1].text
    assert "source:Program.cs#L999" not in response.result[0].text
    assert "引用未核对" in response.result[0].text and "源码核对提示" in response.result[0].text
    assert events[-1][0] == "answer_validation" and not events[-1][1]["passed"]


class EvidenceRepairModel(DeterministicModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if any(
            isinstance(message, ToolMessage) and message.name == "read_source"
            for message in messages
        ):
            answer = AIMessage(content="入口是 Main。[Program.cs:2](source:Program.cs#L2)")
        elif "系统引用核对结果" in messages[-1].text:
            answer = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "read_source",
                        "args": {"path": "Program.cs", "start_line": 2, "end_line": 2},
                        "id": "verify-main",
                    }
                ],
            )
        else:
            answer = AIMessage(content="入口 [Program.cs:999](source:Program.cs#L999)")
        answer.usage_metadata = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
        return ChatResult(generations=[ChatGeneration(message=answer)])


async def test_real_graph_repair_tool_loop_and_usage_are_persisted(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=16384, output_tokens=512)))
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: EvidenceRepairModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("源码证据")
    run = repository.create_run(thread["id"], "解释 Program.cs 的入口方法", [])
    answer = await runtime.execute(
        run, lambda kind, payload: repository.event(run["id"], kind, payload)
    )
    assert "#L2)" in answer and "#L999" not in answer
    events = repository.events(run["id"], 0)
    validation = [event["payload"] for event in events if event["kind"] == "answer_validation"]
    assert validation[-1]["passed"]
    assert any(event["kind"] == "source_evidence" for event in events)
    usage = [event["payload"] for event in events if event["kind"] == "provider_usage"]
    answer_usage = [row for row in usage if row["purpose"] == "answer"]
    assert len(answer_usage) == 3 and all(
        row["reported"] and row["input_tokens"] == 100 for row in answer_usage
    )


def test_duplicate_results_keep_latest_payload_and_call_pairing():
    raw = dump_json({"path": "Program.cs", "version": "a" * 64, "lines": ["源码" * 2000]})
    messages = [ToolMessage(content=raw, name="read_source", tool_call_id=str(i)) for i in range(3)]
    compact = deduplicate_source_results(messages)
    assert compact[-1].text == raw and all(item.text == raw for item in messages)
    assert [item.tool_call_id for item in compact] == ["0", "1", "2"]
    assert estimate_tokens(compact) < estimate_tokens(messages) // 2
    assert deduplicate_source_results(compact) == compact


def test_version_cache_cannot_miss_same_size_and_mtime_replacement(services):
    _, _, workspace, *_ = services
    path = workspace.root / "Program.cs"
    before = workspace.read("Program.cs")
    workspace.symbols("Program.cs")
    workspace.symbols("Program.cs")
    assert workspace.symbol_cache.statistics()["hits"] == 1
    previous = path.stat()
    path.write_bytes(path.read_bytes().replace(b"Program", b"Changed"))
    os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    after = workspace.read("Program.cs")
    assert after["version"] != before["version"] and "Changed" in after["content"]
    assert workspace.symbols("Program.cs")["symbols"][0]["name"] == "Changed"
    cache = VersionCache(max_entries=2, max_bytes=4)
    for number in range(10):
        cache.get_or_create(number, lambda value=number: value, 2)
    assert cache.statistics()["entries"] == 2 and cache.statistics()["bytes"] == 4


def test_missing_usage_is_unknown_and_openai_metadata_is_supported():
    assert reported_usage(AIMessage(content="回答"))["input_tokens"] is None
    message = AIMessage(
        content="回答",
        response_metadata={"token_usage": {"prompt_tokens": 20, "completion_tokens": 5}},
    )
    assert reported_usage(message) == {
        "input_tokens": 20,
        "output_tokens": 5,
        "total_tokens": 25,
        "reported": True,
        "cache_read_tokens": None,
    }


def test_literal_examples_are_not_citations_and_empty_file_has_evidence(services):
    _, _, workspace, *_ = services
    ledger = SourceEvidence(workspace, lambda *_args: None)
    example = "`[例子](source:Missing.cs#L1)`\n```markdown\n[x](source:Missing.cs#L99)\n```"
    assert ledger.check(example)["passed"] and ledger.check(example)["citations"] == []
    (workspace.root / "Empty.cs").write_bytes(b"")
    ledger.required = True
    ledger.record(source_excerpt(workspace, "Empty.cs"))
    assert ledger.check("Empty.cs 是当前核对过的空文件，没有可引用的行。")["passed"]


def test_native_parser_failure_is_isolated_from_source_service(services, monkeypatch):
    from types import SimpleNamespace

    workspace = services[2]
    monkeypatch.setattr(
        "app.modules.source_analysis.workspace.subprocess.run",
        lambda *_a, **_kw: SimpleNamespace(returncode=-1073741819, stdout=""),
    )
    result = workspace.symbols("Program.cs")
    assert result["analysis"] == "unavailable" and result["symbols"] == []
    assert workspace.read("Program.cs")["line_count"] == 3
