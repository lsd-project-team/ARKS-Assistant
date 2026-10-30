"""在同一检查点实际重新生成，覆盖源码缺引用与无关经验组合。"""

import asyncio
import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from sqlalchemy import text

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from app.modules.chat.rich_presentation import rich_documents
from app.modules.chat.runs import RunManager
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.semantic import SemanticRetrieval
from tests.helpers.models import DeterministicModel

QUESTION = "我想在做设备标定，给我输出一下标定流程"


def answer(*, citation=True):
    step = {"id": "one", "title": "入口", "description": "Main 方法体为空，没有后续动作。"}
    if citation:
        step["sources"] = [{"path": "Program.cs", "start_line": 2, "end_line": 2}]
    return (
        "```rich-content\n"
        + json.dumps(
            {
                "version": 1,
                "blocks": [{"id": "flow", "type": "step_flow", "steps": [step]}],
            },
            ensure_ascii=False,
        )
        + "\n```"
    )


@pytest.mark.parametrize("mode", ["cited", "missing_first", "missing_all", "changed", "foreign"])
@pytest.mark.parametrize("rounds", [1, 2])
async def test_real_regeneration_revalidates_prior_reads_and_never_becomes_empty_knowledge(
    services, monkeypatch, mode, rounds
):
    paths, database, workspace, repository, memories, settings = services
    store = DebugIssues(HandoverStore(database=database))
    for topic in ("发货日期", "来料延期", "镜头视野"):
        store.save(
            DebugWrite(
                title="标定设备的" + topic + "记录",
                payload={
                    "problem": "设备标定会议中讨论" + topic,
                    "solution": "等待相关人员确认",
                },
            ),
            {},
        )
    monkeypatch.setattr(SemanticRetrieval, "scores", lambda *_args: {})
    settings.save(AppSettings(model=ModelSettings(context_tokens=32768, output_tokens=4096)))
    calls = {"regenerated": 0, "selection": 0, "reviews": 0}

    class Model(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if "你只负责筛选资料" in messages[0].text:
                calls["selection"] += 1
                result = AIMessage(content='{"selections":[]}')
            elif "独立的源码结论复核器" in messages[0].text:
                calls["reviews"] += 1
                result = AIMessage(content='{"verdict":"passed","issues":[]}')
            elif any((row.id or "").startswith("regenerate:") for row in messages):
                calls["regenerated"] += 1
                cited = mode not in {"missing_all", "missing_first"} or (
                    mode == "missing_first" and calls["regenerated"] > 1
                )
                result = AIMessage(content=answer(citation=cited))
            elif any(
                isinstance(row, ToolMessage) and row.name == "read_source" for row in messages
            ):
                result = AIMessage(content=answer())
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
    manager = RunManager(repository, runtime, settings)
    original = repository.create_run(
        None,
        QUESTION,
        [],
        {
            "use_knowledge": True,
            "use_memory": True,
            "use_deepwiki": True,
        },
    )
    try:
        manager.start(original)
        await asyncio.wait_for(manager.tasks[original["id"]], timeout=20)
        first = repository.run(original["id"])
        assert first["status"] == "completed" and first["answer"] == answer()
        if mode == "changed":
            (workspace.root / "Program.cs").write_text(
                "class Changed {\n static void Main() {}\n}\n", encoding="utf-8"
            )
        elif mode == "foreign":
            stale = repository.run_event(first["id"], "source_evidence")
            stale["source_workspace_id"] = "foreign-source"
            with database.engine.begin() as connection:
                connection.execute(
                    text(
                        "update run_events set payload_json=:payload "
                        "where run_id=:run and kind='source_evidence'"
                    ),
                    {
                        "payload": json.dumps(stale),
                        "run": first["id"],
                    },
                )
        latest = first
        for _generation in range(rounds):
            calls["regenerated"] = 0
            regenerated = repository.regenerate(latest["id"])
            manager.start(regenerated)
            await asyncio.wait_for(manager.tasks[regenerated["id"]], timeout=20)
            saved = repository.run(regenerated["id"])
            assert saved["status"] == "completed", saved.get("error")
            result = saved["answer"]
            assert (
                list(rich_documents(result))
                and "没有选到" not in result
                and "资料筛选" not in result
            )
            assert calls["selection"] == 0
            validation = repository.run_event(saved["id"], "answer_validation")
            verified = mode in {"cited", "missing_first"}
            assert validation["passed"] is verified
            if verified:
                assert result == answer()
                assert calls["regenerated"] == (1 if mode == "cited" else 2)
                assert calls["reviews"] == 0
            else:
                assert "源码核对提示" in result
                assert calls["regenerated"] == 3 and calls["reviews"] == 0
            evidence = [
                row["payload"]
                for row in repository.events(saved["id"])
                if row["kind"] == "source_evidence"
            ]
            if mode in {"changed", "foreign"}:
                assert not evidence
            else:
                # 不再追加模型结论复核读取，重新生成仍复用实际同版本源码。
                model_reads = [row for row in evidence if not row.get("review_only")]
                assert len(model_reads) == 1 and model_reads[0]["reason"] == "regenerate"
                assert model_reads[0]["start_line"] == model_reads[0]["end_line"] == 2
                assert not any(row["reason"] == "source_review" for row in evidence)
            assert repository.run(original["id"])["answer"] == first["answer"]
            events = repository.events(saved["id"])
            assert not any(row["kind"] == "token" for row in events)
            assert [
                row["payload"]["text"] for row in events if row["kind"] == "answer_replace"
            ] == [result]
            assert repository.thread(saved["thread_id"])["messages"][-1]["content"] == result
            assert [row async for row in manager.stream(saved["id"], after=0)] == events
            latest = saved
    finally:
        await manager.shutdown()
        runtime.semantic.close()
