"""真实 Agent 图组合回归：无关经验不能覆盖源码流程，事件回放与历史保持一致。"""

import asyncio
import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from app.modules.chat.rich_presentation import rich_documents, source_pointers
from app.modules.chat.runs import RunManager
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.semantic import SemanticRetrieval
from tests.helpers.models import DeterministicModel

QUESTION = "我想在做设备标定，给我输出一下标定流程"


def flow(description):
    document = {
        "version": 1,
        "blocks": [
            {
                "id": "flow",
                "type": "step_flow",
                "steps": [
                    {
                        "id": "main",
                        "title": "入口",
                        "description": description,
                        "sources": [{"path": "Program.cs", "start_line": 2, "end_line": 2}],
                    }
                ],
            }
        ],
    }
    return "```rich-content\n" + json.dumps(document, ensure_ascii=False) + "\n```"


def seed_unrelated_records(database):
    store = DebugIssues(HandoverStore(database=database))
    for topic in ("发货日期", "来料延期", "镜头视野"):
        store.save(
            DebugWrite(
                title="标定设备的" + topic + "记录",
                payload={"problem": "设备标定会议中讨论" + topic, "solution": "等待相关人员确认"},
            ),
            {},
        )


@pytest.mark.parametrize("presentation", ["markdown", "rich", "composed"])
@pytest.mark.parametrize("use_knowledge", [True, False])
@pytest.mark.parametrize("verdict", ["passed", "unknown"])
async def test_unrelated_knowledge_does_not_replace_source_flow_or_trigger_repairs(
    services, monkeypatch, presentation, use_knowledge, verdict
):
    paths, database, workspace, repository, memories, settings = services
    seed_unrelated_records(database)
    # 此用例检查生成和核查的组合，词面命中仍真实执行，不依赖本机向量模型。
    monkeypatch.setattr(SemanticRetrieval, "scores", lambda *_args: {})
    settings.save(AppSettings(model=ModelSettings(context_tokens=32768, output_tokens=4096)))
    compact = flow("Main 方法体为空，没有后续动作。")
    if presentation == "markdown":
        compact = "1. Main 方法体为空，没有后续动作。[源码](source:Program.cs#L2-L2)"
    draft = flow("尚待整理的冗长流程说明。" * 200) if presentation == "composed" else compact
    phases = []

    class Model(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            try:
                payload = json.loads(messages[-1].text)
            except ValueError:
                payload = {}
            if "你只负责筛选资料" in messages[0].text:
                phases.append("knowledge_selection")
                result = AIMessage(content='{"selections":[]}')
            elif "draft" in payload and "question" in payload:
                assert payload["draft"] == draft
                phases.append("compose")
                result = AIMessage(content=compact)
            elif "answer" in payload and "source" in payload:
                assert "Main 方法体为空" in payload["answer"]
                phases.append("review")
                result = AIMessage(content=json.dumps({"verdict": verdict, "issues": []}))
            elif any(
                isinstance(row, ToolMessage) and row.name == "read_source" for row in messages
            ):
                phases.append("answer")
                result = AIMessage(content=draft)
            else:
                phases.append("read")
                result = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "entry",
                            "name": "read_source",
                            "args": {"path": "Program.cs", "start_line": 2, "end_line": 2},
                        }
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=result)])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    manager = RunManager(repository, runtime, settings)
    question = QUESTION + ("，使用纯Markdown" if presentation == "markdown" else "")
    run = repository.create_run(
        None,
        question,
        [],
        {"use_knowledge": use_knowledge, "use_deepwiki": False, "use_memory": False},
    )
    try:
        manager.start(run)
        await asyncio.wait_for(manager.tasks[run["id"]], timeout=20)
        saved = repository.run(run["id"])
        assert saved["status"] == "completed", saved.get("error")
        answer = saved["answer"]
        if verdict == "passed":
            assert answer == compact
        else:
            assert answer.startswith(compact)
        events = repository.events(run["id"])
        context = repository.run_event(run["id"], "context_sources")
        assert context["debug_issues"] == []
        assert not any(event["kind"] == "knowledge_search" for event in events)
        assert phases == [
            "read",
            "answer",
            *(["compose"] if presentation == "composed" else []),
            "review",
        ]
        assert repository.run_event(run["id"], "source_review")["verdict"] == verdict
        validation = repository.run_event(run["id"], "answer_validation")
        assert validation["passed"] and all(row["valid"] for row in validation["citations"])
        assert len(validation["citations"]) == 1
        assert "没有选到" not in answer and "源码回答缺少" not in answer
        assert "等待相关人员确认" not in answer
        assert not any(event["kind"] in {"token", "knowledge_selection"} for event in events)
        assert [
            event["payload"]["text"] for event in events if event["kind"] == "answer_replace"
        ] == [answer]
        assert repository.thread(run["thread_id"])["messages"][-1]["content"] == answer
        replay = [event async for event in manager.stream(run["id"], after=0)]
        assert replay == events and replay[-1]["payload"]["answer"] == answer
        if presentation != "markdown":
            assert all(document is not None for _, _, document in rich_documents(answer))
            assert [pointer.path for pointer in source_pointers(answer)] == ["Program.cs"]
    finally:
        await manager.shutdown()
        runtime.semantic.close()


@pytest.mark.parametrize("defect", ["path", "version", "workspace", "claim"])
async def test_source_guard_still_repairs_unverified_source_with_unrelated_knowledge(
    services, monkeypatch, defect
):
    paths, database, workspace, repository, memories, settings = services
    seed_unrelated_records(database)
    monkeypatch.setattr(SemanticRetrieval, "scores", lambda *_args: {})
    settings.save(AppSettings(model=ModelSettings(context_tokens=32768, output_tokens=4096)))
    corrected = flow("Main 方法体为空。")
    broken = {
        "path": corrected.replace('"Program.cs"', '"Missing.cs"'),
        "version": corrected.replace('"start_line": 2', '"version":"wrong","start_line": 2'),
        "workspace": corrected.replace(
            '"start_line": 2', '"source_workspace_id":"foreign","start_line": 2'
        ),
        "claim": flow("Main 会启动设备。"),
    }[defect]
    calls = []

    class Model(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            try:
                payload = json.loads(messages[-1].text)
            except ValueError:
                payload = {}
            if "answer" in payload and "source" in payload:
                calls.append("review")
                value = {"verdict": "passed", "issues": []}
                if "Main 会启动设备" in payload["answer"]:
                    value = {
                        "verdict": "needs_correction",
                        "issues": [
                            {"claim": "Main 会启动设备。", "reason": "Program.cs:2 方法体为空"}
                        ],
                    }
                result = AIMessage(content=json.dumps(value))
            elif any(
                isinstance(row, ToolMessage) and row.name == "read_source" for row in messages
            ):
                calls.append("answer")
                result = AIMessage(content=corrected if calls.count("answer") > 1 else broken)
            else:
                result = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "entry",
                            "name": "read_source",
                            "args": {"path": "Program.cs", "start_line": 2, "end_line": 2},
                        }
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=result)])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    run = repository.create_run(None, QUESTION, [])
    try:
        answer = await runtime.execute(
            run, lambda kind, payload: repository.event(run["id"], kind, payload)
        )
        assert answer == corrected and calls.count("answer") == 2
        assert calls.count("review") == (2 if defect == "claim" else 1)
        assert repository.run_event(run["id"], "answer_validation")["passed"]
        assert repository.run_event(run["id"], "source_review")["verdict"] == "passed"
        assert repository.run_event(run["id"], "context_sources")["debug_issues"] == []
        assert not any(
            event["kind"] == "knowledge_search" for event in repository.events(run["id"])
        )
    finally:
        runtime.semantic.close()


@pytest.mark.parametrize("with_history", [False, True])
@pytest.mark.parametrize("defect", ["range", "version", "workspace"])
async def test_exhausted_source_repairs_keep_flow_and_disable_only_unverified_links(
    services, monkeypatch, with_history, defect
):
    paths, database, workspace, repository, memories, settings = services
    seed_unrelated_records(database)
    monkeypatch.setattr(SemanticRetrieval, "scores", lambda *_args: {})
    settings.save(AppSettings(model=ModelSettings(context_tokens=32768, output_tokens=4096)))
    document = json.loads(flow("Main 方法体为空；其余流程本轮尚未核实。").splitlines()[1])
    invalid = {"path": "Program.cs", "start_line": 3, "end_line": 3}
    if defect != "range":
        invalid.update(start_line=2, end_line=2)
        invalid["version" if defect == "version" else "source_workspace_id"] = "foreign"
    document["blocks"][0]["steps"][0]["sources"].append(invalid)
    draft = "```rich-content\n" + json.dumps(document, ensure_ascii=False) + "\n```"
    answers = []

    class Model(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if any(isinstance(row, ToolMessage) and row.name == "read_source" for row in messages):
                # 模拟模型补核对两次后仍沿用了历史范围或错误元数据，不能假装引用已通过。
                answers.append(draft)
                result = AIMessage(content=draft)
            else:
                result = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "current-entry",
                            "name": "read_source",
                            "args": {"path": "Program.cs", "start_line": 2, "end_line": 2},
                        }
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=result)])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    manager = RunManager(repository, runtime, settings)
    thread_id = None
    if with_history:
        previous = repository.create_run(None, "以前的标定流程", [])
        repository.finish(previous["id"], "旧范围。[旧引用](source:Program.cs#L3-L3)")
        thread_id = previous["thread_id"]
    run = repository.create_run(
        thread_id,
        QUESTION,
        [],
        {"use_knowledge": True, "use_deepwiki": False, "use_memory": False},
    )
    try:
        manager.start(run)
        await asyncio.wait_for(manager.tasks[run["id"]], timeout=20)
        saved = repository.run(run["id"])
        assert saved["status"] == "completed", saved.get("error")
        answer = saved["answer"]
        documents = [doc for _, _, doc in rich_documents(answer)]
        assert documents and all(doc is not None for doc in documents)
        assert documents[0].blocks[0].type == "step_flow"
        assert (
            documents[0].blocks[0].steps[0].description == "Main 方法体为空；其余流程本轮尚未核实。"
        )
        assert "引用未核对" in answer and "源码核对提示" in answer
        assert len(answers) == 3
        # 同一路径/行号有伪造版本时全部停用，避免为冲突来源背书。
        pointers = list(source_pointers(answer))
        assert len(pointers) == (1 if defect == "range" else 0)
        assert not pointers or pointers[0].start_line == 2
        validation = repository.run_event(run["id"], "answer_validation")
        assert not validation["passed"] and any(not row["valid"] for row in validation["citations"])
        events = repository.events(run["id"])
        assert not any(
            event["kind"] in {"token", "knowledge_selection", "source_review"} for event in events
        )
        assert [
            event["payload"]["text"] for event in events if event["kind"] == "answer_replace"
        ] == [answer]
        assert repository.thread(run["thread_id"])["messages"][-1]["content"] == answer
        assert [event async for event in manager.stream(run["id"], after=0)] == events
    finally:
        await manager.shutdown()
        runtime.semantic.close()
