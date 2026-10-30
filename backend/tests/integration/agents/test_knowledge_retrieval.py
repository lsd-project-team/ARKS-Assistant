"""真实临时问题库和工具边界：回答模型不能看到未经筛选的候选。"""

import asyncio
import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.context.tokens import estimate_tokens
from app.agents.runtime.engine import AgentRuntime
from app.agents.runtime.knowledge_selection import KnowledgeRetrieval
from app.core.config import AppSettings, ModelSettings
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.debug_lookup import DebugIssueLookup
from app.modules.knowledge.semantic import SemanticRetrieval
from tests.helpers.models import DeterministicModel, fixture_selections


class Selector:
    def __init__(self, choice=None):
        self.choice, self.requests = choice, []

    async def ainvoke(self, messages, **kwargs):
        payload = json.loads(messages[-1].text)
        assert "answer" not in payload
        self.requests.append(payload)
        if isinstance(self.choice, BaseException):
            raise self.choice
        value = self.choice
        if value is None:
            value = {"scope": "records", "selections": fixture_selections(payload["records"])}
        elif callable(value):
            value = value(payload)
        return AIMessage(content=value if isinstance(value, str) else json.dumps(value))


@pytest.fixture
def issues(services, monkeypatch):
    # 所有合成记录都成为候选，筛选必须实际去掉无关日期和记录。
    monkeypatch.setattr(
        SemanticRetrieval, "scores", lambda _self, _query, documents: dict.fromkeys(documents, 0.9)
    )
    return DebugIssues(HandoverStore(database=services[1]))


def retrieval(services, selector, question="查询10月1日的试验结果", **kwargs):
    events = []

    def emit(*row):
        events.append(row)

    lookup = DebugIssueLookup(services[1], emit, question)
    return KnowledgeRetrieval(
        lookup, selector, question, emit, kwargs.pop("limit", 16000), **kwargs
    ), events


async def test_search_filters_records_and_spans_before_returning_tool_context(services, issues):
    saved = issues.save(
        DebugWrite(
            title="阀门试验", payload={"problem": "10月1日试验结果为42。10月9日无关结果999。"}
        ),
        {},
    )
    other = issues.save(
        DebugWrite(title="无关候选的标题", payload={"problem": "10月9日另一设备的私有候选888。"}),
        {},
    )

    def choose(payload):
        selected = next(row for row in payload["records"] if row["title"] == "阀门试验")
        return {
            "scope": "records",
            "selections": [
                {"id": selected["id"], "parts": [{"field": "问题", "start": 1, "end": 1}]}
            ],
        }

    selector = Selector(choose)
    selected, events = retrieval(services, selector)
    tools = {tool.name: tool for tool in selected.tools()}
    result = json.loads(await tools["search_debug_issues"].ainvoke({"query": "试验"}))
    assert len(selector.requests[0]["records"]) == 2
    assert result["matches"][0]["content"] == {"问题": "10月1日试验结果为42。"}
    assert result["matched"] == 1 and result["selection_status"] == "selected"
    assert "resolution_status" not in json.dumps(result)
    assert all(
        text not in json.dumps(result, ensure_ascii=False)
        for text in ("999", "888", other["title"])
    )
    # 后续按编号读取也不能绕过筛选，已筛选同版本不再请求模型。
    page = json.loads(await tools["read_debug_issue"].ainvoke({"record_id": saved["id"]}))
    assert "42" in page["content"] and "999" not in page["content"]
    assert "resolution_status" not in json.dumps(page)
    rejected = json.loads(await tools["read_debug_issue"].ainvoke({"record_id": other["id"]}))
    assert rejected["content"] == "" and rejected["selection_status"] == "none"
    assert len(selector.requests) == 1
    assert "999" in str(selected.review_records()) and "888" not in str(selected.review_records())
    assert [row["id"] for kind, row in events if kind == "knowledge_reference"] == [saved["id"]]
    assert [row["resolution_status"] for kind, row in events if kind == "knowledge_reference"] == [
        "open"
    ]


@pytest.mark.parametrize(
    "choice", ["not json", RuntimeError("secret-value"), {"selections": [{"id": 999, "parts": []}]}]
)
async def test_selection_failure_never_falls_back_to_raw_candidates(services, issues, choice):
    saved = issues.save(
        DebugWrite(title="不许泄漏候选标题", payload={"problem": "原始候选内容771。"}), {}
    )
    selector = Selector(choice)
    selected, events = retrieval(services, selector)
    result = await selected.search_report("试验")
    assert result["selection_status"] == "unavailable" and result["matches"] == []
    assert "处理失败" in result["notice"] and "不代表资料库没有" in result["notice"]
    assert all(value not in str(result) for value in (saved["title"], "771", "secret-value"))
    assert selected.review_records() == []
    assert not any(kind == "knowledge_reference" for kind, _ in events)
    assert "secret-value" not in str(events)


async def test_empty_search_and_valid_empty_selection_are_not_processing_failures(services, issues):
    selector = Selector({"scope": "records", "selections": []})
    selected, events = retrieval(services, selector)
    result = await selected.search_report("试验")
    assert result["selection_status"] == "none" and not selector.requests
    issues.save(DebugWrite(title="后来写入的试验", payload={"problem": "结果99。"}), {})
    # 首轮固定空快照，下一轮才看到新增记录。
    result = await selected.search_report("试验")
    assert result["selection_status"] == "none" and not selector.requests
    next_run, _ = retrieval(services, selector)
    result = await next_run.search_report("试验")
    assert result["selection_status"] == "none" and len(selector.requests) == 1
    assert "处理失败" not in result["notice"] and not result["matches"]
    assert not any(kind == "knowledge_reference" for kind, _ in events)


async def test_followup_selection_uses_context_and_final_check_receives_same_context(
    services, issues
):
    from app.agents.context.retrieval_context import retrieval_context
    from app.agents.runtime.knowledge_answer import KnowledgeAnswerGuard

    saved = issues.save(
        DebugWrite(title="设备B V3报警", payload={"problem": "设备B V3结果42。"}), {}
    )
    context = retrieval_context([{"role": "user", "content": "纠正：现在问设备B V3。"}])
    selector = Selector()
    selected, _ = retrieval(services, selector, question="它当时怎么解决的？", context=context)
    await selected.read(saved["id"])
    assert selector.requests[0]["context"] == context
    assert selector.requests[0]["question"] == "它当时怎么解决的？"

    class Reviewer:
        async def ainvoke(self, messages, **kwargs):
            payload = json.loads(messages[-1].text)
            assert payload["context"] == context and "设备B V3" in str(payload["context"])
            return AIMessage(content='{"verdict":"passed","answer":""}')

    guard = KnowledgeAnswerGuard(
        Reviewer(),
        "它当时怎么解决的？",
        selected.review_records,
        lambda *_: None,
        16000,
        preselected=selected.selected,
        context=context,
    )
    assert (
        await guard.verify("结果42。", selected.selected()[1], selected.review_records())
        == "结果42。"
    )


async def test_parallel_search_and_read_share_one_selection_and_frozen_version(services, issues):
    saved = issues.save(
        DebugWrite(
            title="阀门试验",
            payload={
                "problem": "原始结果42。",
                "resolution_status": "resolved",
                "solution": "按记录方法处理",
            },
        ),
        {},
    )
    selector = Selector()
    selected, events = retrieval(services, selector)
    results = await asyncio.gather(*[selected.read(saved["id"]) for _ in range(5)])
    assert len(selector.requests) == 1 and all("42" in row["content"] for row in results)
    issues.save(
        DebugWrite(title=saved["title"], payload={"problem": "新结果99。"}, version=1),
        {},
        saved["id"],
    )
    page = await selected.read(saved["id"])
    assert page["version"] == 1 and "99" not in page["content"]
    assert len([row for kind, row in events if kind == "knowledge_reference"]) == 1
    assert [row["resolution_status"] for kind, row in events if kind == "knowledge_reference"] == [
        "resolved"
    ]
    next_run, _ = retrieval(services, Selector())
    assert "99" in (await next_run.read(saved["id"]))["content"]


async def test_known_reference_is_selected_without_semantic_search_and_wrong_version_is_rejected(
    services, issues, monkeypatch
):
    saved = issues.save(DebugWrite(title="阀门试验", payload={"problem": "原始结果42。"}), {})
    monkeypatch.setattr(SemanticRetrieval, "scores", lambda *_: pytest.fail("按引用核对不应搜索"))
    selector = Selector()
    selected, events = retrieval(services, selector)
    assert await selected.resolve_references({f"debug-issue:{saved['id']}/99"}) == []
    assert not selector.requests
    records = await selected.resolve_references({f"debug-issue:{saved['id']}/1"})
    assert len(records) == 1 and len(selector.requests) == 1
    assert "42" in str(records)
    assert not any(kind == "knowledge_search" for kind, _ in events)


@pytest.mark.parametrize("fail_second", [False, True])
async def test_selection_batches_preserve_ids_and_never_publish_partial_success(
    services, issues, fail_second
):
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.agents.runtime.knowledge_scope import SELECTION_GUIDANCE
    from app.core.config import dump_json

    saved = [
        issues.save(DebugWrite(title=f"试验{n}", payload={"problem": "合成正文。" * 120}), {})
        for n in range(2)
    ]
    calls = []

    def choose(payload):
        calls.append(payload)
        if fail_second and len(calls) == 2:
            raise RuntimeError("筛选第二批失败")
        return {"scope": "records", "selections": fixture_selections(payload["records"])}

    selected, events = retrieval(services, Selector(choose))
    records = selected.lookup.snapshot_records([row["id"] for row in saved])
    limit = (
        max(
            estimate_tokens(
                [
                    SystemMessage(content=SELECTION_GUIDANCE),
                    HumanMessage(content=dump_json(selected.selector.payload([row]))),
                ]
            )
            for row in records
        )
        + 256
    )
    selected.selector.calls.input_limit = limit
    result = await selected.search_report("试验")
    assert len(calls) == 2
    if fail_second:
        assert result["selection_status"] == "unavailable" and not result["matches"]
        assert selected.review_records() == []
        assert not any(kind == "knowledge_reference" for kind, _ in events)
    else:
        assert {row["id"] for row in result["matches"]} == {row["id"] for row in saved}
        assert len([kind for kind, _ in events if kind == "knowledge_reference"]) == 2


@pytest.mark.parametrize("kind", ["budget", "timeout", "cancel"])
async def test_budget_timeout_and_cancellation_do_not_expose_candidates(services, issues, kind):
    saved = issues.save(DebugWrite(title="阀门试验", payload={"problem": "原始结果42。"}), {})

    class Slow(Selector):
        async def ainvoke(self, *args, **kwargs):
            await asyncio.Event().wait()

    selector = Slow() if kind == "timeout" else Selector(asyncio.CancelledError())
    selected, events = retrieval(
        services,
        selector,
        limit=1 if kind == "budget" else 16000,
        timeout=0.01 if kind == "timeout" else 30,
    )
    if kind == "cancel":
        with pytest.raises(asyncio.CancelledError):
            await selected.read(saved["id"])
    else:
        result = await selected.read(saved["id"])
        assert result["content"] == "" and result["selection_status"] == "unavailable"
    assert selected.review_records() == []
    assert not any(kind == "knowledge_reference" for kind, _ in events)


async def test_answer_model_only_sees_selected_content_and_final_facts_are_still_corrected(
    services, issues, monkeypatch
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(model=ModelSettings(context_tokens=16384, output_tokens=1024), mcp_servers=[])
    )
    saved = issues.save(
        DebugWrite(title="阀门试验", payload={"problem": "本次结果42。其他时段为999。"}), {}
    )
    issues.save(DebugWrite(title="不该进入回答的候选", payload={"problem": "无关结果888。"}), {})
    reference = f"[阀门试验](debug-issue:{saved['id']}/1)"
    corrected = "本次结果为42。" + reference
    phases, answer_inputs, checks = [], [], []

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            if "你只负责筛选资料" in messages[0].text:
                phases.append("selection")
                payload = json.loads(messages[-1].text)
                row = next(row for row in payload["records"] if row["title"] == "阀门试验")
                answer = AIMessage(
                    content=json.dumps(
                        {
                            "scope": "records",
                            "selections": [
                                {
                                    "id": row["id"],
                                    "parts": [{"field": "问题", "start": 1, "end": 1}],
                                }
                            ],
                        }
                    )
                )
            elif "你负责核查历史经验回答" in messages[0].text:
                phases.append("verification")
                checks.append(json.loads(messages[-1].text))
                answer = AIMessage(
                    content=json.dumps(
                        {
                            "verdict": "passed" if checks[-1]["answer"] == corrected else "revised",
                            "reason": "数值应为42",
                            "answer": "" if checks[-1]["answer"] == corrected else corrected,
                        }
                    )
                )
            else:
                phases.append("answer")
                answer_inputs.append(messages)
                if not any(isinstance(row, ToolMessage) for row in messages):
                    answer = AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "search",
                                "name": "search_debug_issues",
                                "args": {"query": "试验"},
                            }
                        ],
                    )
                else:
                    answer = AIMessage(content="本次结果43。" + reference)
            return ChatResult(generations=[ChatGeneration(message=answer)])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    run = repository.create_run(
        None,
        "查询本次试验结果",
        [],
        {"use_memory": False, "use_knowledge": True, "use_deepwiki": False},
    )
    events = []
    try:
        answer = await runtime.execute(run, lambda *row: events.append(row))
        assert answer == corrected
        assert phases == ["answer", "selection", "answer", "verification", "verification"]
        context = str([row.content for messages in answer_inputs for row in messages])
        # 随机 UUID 也可能包含 888/999；检查事实原句，避免把合法记录编号误判为泄漏。
        assert "本次结果42" in context
        assert "无关结果888" not in context and "其他时段为999" not in context
        assert "不该进入回答的候选" not in context
        assert all("无关结果888" not in str(payload) for payload in checks)
        assert "999" in str(checks[0]["record_context"])
        assert not any('"selections"' in row["text"] for kind, row in events if kind == "token")
        assert [row["id"] for kind, row in events if kind == "knowledge_reference"] == [saved["id"]]
    finally:
        runtime.semantic.close()


@pytest.mark.parametrize("scope", ["records", "general", "unavailable"])
async def test_empty_preselection_preserves_general_answer_but_blocks_invented_history(
    services, issues, monkeypatch, scope
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(mcp_servers=[]))
    issues.save(DebugWrite(title="阀门试验", payload={"problem": "历史结果42。"}), {})

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            if "你只负责筛选资料" in messages[0].text:
                answer = AIMessage(
                    content=(
                        "invalid"
                        if scope == "unavailable"
                        else json.dumps({"scope": scope, "selections": []})
                    )
                )
            elif "你负责核查历史经验回答" in messages[0].text:
                pytest.fail("无选定资料时不能调用事实核查或把候选作为核查依据")
            elif any(isinstance(row, ToolMessage) for row in messages):
                # 即使主模型编造没有引用的数字，历史查询的空筛选也必须拦住。
                answer = AIMessage(content="普通说明。" if scope == "general" else "试验结果42。")
            else:
                answer = AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "search", "name": "search_debug_issues", "args": {"query": "试验"}}
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=answer)])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    run = repository.create_run(
        None,
        "查询本次试验结果",
        [],
        {"use_memory": False, "use_knowledge": True, "use_deepwiki": False},
    )
    events = []
    try:
        answer = await runtime.execute(run, lambda *row: events.append(row))
        assert "42" not in answer
        assert not any(
            "42" in row["text"] for kind, row in events if kind in {"token", "answer_replace"}
        )
        if scope == "records":
            assert "没有选到" in answer and "处理失败" not in answer
        elif scope == "unavailable":
            assert "资料筛选暂未完成" in answer and "不代表资料库没有" in answer
        else:
            assert answer == "普通说明。"
    finally:
        runtime.semantic.close()
