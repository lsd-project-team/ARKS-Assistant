import json

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.context.task_guidance import SOURCE_ANSWER_NOTE_ID
from app.agents.runtime.engine import AgentRuntime
from app.modules.chat.context import ConversationContext
from app.modules.chat.runs import RunManager
from tests.helpers.models import DeterministicModel


class TruncatedSourceModel(DeterministicModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if "独立的源码结论复核器" in messages[0].text:
            answer = AIMessage(content=json.dumps({"verdict": "passed", "issues": []}))
        elif "系统输出恢复" in messages[-1].text:
            answer = AIMessage(
                content="也需要验收记录。", response_metadata={"stop_reason": "end_turn"}
            )
        else:
            reads = [
                item
                for item in messages
                if isinstance(item, ToolMessage) and item.name == "read_source"
            ]
            if len(reads) < 2:
                answer = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": f"read-{len(reads)}",
                            "name": "read_source",
                            "args": {"path": "Program.cs", "start_line": 1, "end_line": 3},
                        }
                    ],
                )
            else:
                answer = AIMessage(
                    content="入口有实现。[源码](source:Program.cs#L1-L3)\n进度",
                    response_metadata={"stop_reason": "max_tokens"},
                )
        return ChatResult(generations=[ChatGeneration(message=answer)])


async def test_graph_continuation_cache_final_validation_and_persisted_status(
    services, monkeypatch
):
    paths, _, workspace, repository, memory, settings = services
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: TruncatedSourceModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memory)
    manager = RunManager(repository, runtime, settings)
    run = repository.create_run(None, "这个项目未完成的进度到哪里了", [], {"use_knowledge": False})
    manager.start(run)
    await manager.tasks[run["id"]]
    saved = repository.run(run["id"])
    assert saved["status"] == "completed" and saved["answer"].endswith("进度也需要验收记录。")
    assert saved["model_snapshot"]["output_tokens"] == 8192
    completion = repository.run_event(run["id"], "run_completion")
    assert completion["output"] == "complete" and completion["continuations"] == 1
    assert completion["counts"]["success"] == 2 and completion["counts"]["cached"] == 1
    context = ConversationContext(runtime).run_sources(run["id"])
    assert context["answer_validation"]["passed"]
    assert context["tools"][1]["cached"]
    assert context["analysis_progress"]["pending"] == []
    assert context["analysis_plan"]["mode"] == "deep"
    assert any(
        event["kind"] == "provider_usage" and event["payload"].get("stop_reason") == "max_tokens"
        for event in repository.events(run["id"])
    )
    runtime.semantic.close()


class BudgetSequenceModel(DeterministicModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if "独立的源码结论复核器" in messages[0].text:
            answer = AIMessage(content='{"verdict":"passed","issues":[]}')
        else:
            tools = [item for item in messages if isinstance(item, ToolMessage)]
            if len(tools) < 9:
                start = len(tools) + 1
                answer = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": f"r-{start}",
                            "name": "read_source",
                            "args": {"path": "Long.cs", "start_line": start, "end_line": start},
                        }
                    ],
                )
            else:
                answer = AIMessage(
                    content="仅核查前八行。[已读](source:Long.cs#L1-L8)",
                    response_metadata={"finish_reason": "stop"},
                )
        return ChatResult(generations=[ChatGeneration(message=answer)])


class BatchVisibleModel(DeterministicModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        messages = [row for row in messages if row.id != SOURCE_ANSWER_NOTE_ID]
        if isinstance(messages[-1], ToolMessage):
            result = json.loads(messages[-1].text)
            assert len(messages[-1].text) > 16000, "覆盖旧的 4000 token 转存阈值"
            assert len(result["reads"][0]["lines"]) == 300
            answer = AIMessage(
                content="批量正文直接可读。", response_metadata={"stop_reason": "end_turn"}
            )
        else:
            answer = AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "batch-large",
                        "name": "read_source_batch",
                        "args": {
                            "ranges": [{"path": "Batch.cs", "start_line": 1, "end_line": 300}]
                        },
                    }
                ],
            )
        return ChatResult(generations=[ChatGeneration(message=answer)])


async def test_bounded_batch_is_not_evicted_to_single_line_scratch_file(services, monkeypatch):
    paths, _, workspace, repository, memory, settings = services
    (workspace.root / "Batch.cs").write_text(
        "\n".join("// " + "source-visible " * 2 for _ in range(300))
    )
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: BatchVisibleModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memory)
    run = repository.create_run(None, "验收批量工具", [], {"use_knowledge": False})
    answer = await runtime.execute(run, lambda *_: None)
    assert answer == "批量正文直接可读。"
    runtime.semantic.close()


async def test_partial_run_keeps_pending_target_and_continue_reuses_evidence(services, monkeypatch):
    paths, _, workspace, repository, memory, settings = services
    configured = settings.load()
    configured.analysis.standard_calls = 8
    configured.analysis.verification_reserve = 2
    settings.save(configured)
    (workspace.root / "Long.cs").write_text("\n".join(f"// {line}" for line in range(12)))
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: BudgetSequenceModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memory)
    manager = RunManager(repository, runtime, settings)
    run = repository.create_run(None, "读取源码核查", [], {"use_knowledge": False})
    manager.start(run)
    await manager.tasks[run["id"]]
    saved = repository.run(run["id"])
    assert saved["status"] == "completed" and saved["stage"] == "partial_review"
    progress = repository.run_event(run["id"], "analysis_progress")
    assert len(progress["pending"]) == 1 and progress["pending"][0]["start_line"] == 9
    completion = repository.run_event(run["id"], "run_completion")
    assert completion["counts"]["skipped"] == 1 and completion["counts"]["success"] == 8

    class ContinueModel(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            messages = [row for row in messages if row.id != SOURCE_ANSWER_NOTE_ID]
            if "独立的源码结论复核器" in messages[0].text:
                answer = AIMessage(content='{"verdict":"passed","issues":[]}')
            elif isinstance(messages[-1], ToolMessage):
                answer = AIMessage(
                    content="补读第九行。[新读](source:Long.cs#L9) [复用](source:Long.cs#L1)"
                )
            else:
                assert "剩余目标" in messages[0].text
                answer = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "remaining-9",
                            "name": "read_source",
                            "args": {"path": "Long.cs", "start_line": 9, "end_line": 9},
                        }
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=answer)])

    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_args, **_kwargs: ContinueModel()
    )
    following = repository.create_run(run["thread_id"], "继续核查", [], {"use_knowledge": False})
    manager.start(following)
    await manager.tasks[following["id"]]
    next_progress = repository.run_event(following["id"], "analysis_progress")
    assert not next_progress["pending"]
    assert any(item["reason"] == "reuse_previous_analysis" for item in next_progress["reads"])
    assert repository.run_event(following["id"], "run_completion")["counts"]["success"] == 1
    assert (
        repository.run_event(following["id"], "run_completion")["semantic_review"]["verdict"]
        == "passed"
    )
    runtime.semantic.close()
