import json

from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.runtime.engine import AgentRuntime
from app.modules.chat.rich_presentation import rich_documents
from app.modules.source_analysis.evidence import (
    SourceEvidence,
    SourceEvidenceGuard,
    mark_unknown_conclusions,
    source_excerpt,
)
from tests.helpers.models import DeterministicModel


class SequenceReviewModel(DeterministicModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if "独立的源码结论复核器" in messages[0].text:
            incorrect = "全部返回在 Move 前" in messages[-1].text
            answer = AIMessage(
                content=json.dumps(
                    {
                        "verdict": "needs_correction" if incorrect else "passed",
                        "issues": [
                            {
                                "claim": "全部返回在 Move 前",
                                "reason": "Program.cs 第4行调用 Move，"
                                "第5行仍会返回 false，顺序相反。",
                            }
                        ]
                        if incorrect
                        else [],
                    },
                    ensure_ascii=False,
                )
            )
        elif "本轮源码结论复核发现" in messages[-1].text:
            answer = AIMessage(
                content="最后一次 return false 在 Move 调用之后。[依据](source:Program.cs#L4-L5)"
            )
        else:
            answer = AIMessage(content="全部返回在 Move 前。[依据](source:Program.cs#L3-L5)")
        return ChatResult(generations=[ChatGeneration(message=answer)])


async def test_long_flow_is_composed_before_source_fact_check_and_final_text_is_displayed(
    services, monkeypatch
):
    paths, _, workspace, repository, memory, settings = services
    read = workspace.read("Program.cs")
    reference = "[依据](source:Program.cs#L1-L3)"
    short = "启动流程：读取入口后再分析调用关系，设备动作仍需核对。" + reference
    checked = []

    class Model(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if "你只负责把流程草稿" in messages[0].text:
                text = short
            elif "独立的源码结论复核器" in messages[0].text:
                checked.append(json.loads(messages[-1].text)["answer"])
                text = json.dumps({"verdict": "passed", "issues": []})
            else:
                text = "流程背景。" * 350 + reference
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memory)
    run = repository.create_run(
        None,
        "根据源码选区给出设备启动流程",
        [
            {
                "path": "Program.cs",
                "start_line": 1,
                "end_line": 3,
                "content": "\n".join(read["content"].splitlines()[:3]),
                "version": read["version"],
            }
        ],
    )
    events = []
    answer = await runtime.execute(run, lambda *e: events.append(e))
    repository.finish(run["id"], answer)
    assert answer == short and checked == [short]
    assert repository.thread(run["thread_id"])["messages"][-1]["content"] == short
    assert not any(kind == "token" for kind, _ in events)
    assert any(kind == "answer_replace" and row["text"] == short for kind, row in events)
    runtime.semantic.close()


async def test_semantic_correction_and_review_stream_are_separate(services, monkeypatch):
    paths, _, workspace, repository, memory, settings = services
    (workspace.root / "Program.cs").write_text(
        "class Program {\n bool Ready() {\n if (false) return false;\n Move();\n"
        " if (false) return false;\n return true;\n }\n void Move() {}\n}"
    )
    source = workspace.read("Program.cs")
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: SequenceReviewModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memory)
    run = repository.create_run(
        None,
        "解释选区函数的提前返回顺序",
        [
            {
                "path": "Program.cs",
                "start_line": 2,
                "end_line": 7,
                "content": "\n".join(source["content"].splitlines()[1:7]),
                "version": source["version"],
            }
        ],
    )
    events = []
    answer = await runtime.execute(run, lambda *event: events.append(event))
    assert "Move 调用之后" in answer and "全部返回在 Move 前" not in answer
    reviews = [payload["verdict"] for kind, payload in events if kind == "source_review"]
    assert reviews == ["needs_correction", "passed"]
    assert not any('"verdict"' in payload["text"] for kind, payload in events if kind == "token")
    runtime.semantic.close()


async def test_unknown_mechanism_is_visible_in_final_reply(services):
    workspace = services[2]
    ledger = SourceEvidence(workspace, lambda *_: None, required=True)
    ledger.record(source_excerpt(workspace, "Program.cs", 1, 3))

    class UnknownReviewer:
        async def ainvoke(self, *_args, **_kwargs):
            return AIMessage(
                content=json.dumps(
                    {
                        "verdict": "unknown",
                        "issues": [],
                        "reason": "Program.cs:2 仅有调用点，外部库的参数机制未核实。",
                    },
                    ensure_ascii=False,
                )
            )

    async def handler(_request):
        return ModelResponse(result=[AIMessage(content="调用点在[这里](source:Program.cs#L2)。")])

    guard = SourceEvidenceGuard(ledger, UnknownReviewer())
    result = await guard.awrap_model_call(
        ModelRequest(model=DeterministicModel(), messages=[]), handler
    )
    assert "结论复核提示" in result.result[0].text and "参数机制未核实" in result.result[0].text


def test_unsupported_mechanism_is_removed_but_its_verified_citation_remains():
    claim = "参数 false 必然选择某种渲染机制。[调用点](source:Program.cs#L2)"
    result = mark_unknown_conclusions(
        "传入 false。" + claim,
        {"issues": [{"claim": claim}], "reason": "只读到调用点，没有外部实现。"},
    )
    assert "必然选择" not in result and "传入 false" in result
    assert "source:Program.cs#L2" in result and "具体机制本轮未核实" in result


def test_unknown_review_without_specific_claims_preserves_steps_and_table():
    original = (
        "```rich-content\n"
        + json.dumps(
            {
                "version": 1,
                "blocks": [
                    {
                        "id": "steps",
                        "type": "step_flow",
                        "steps": [{"id": "stop", "title": "停止", "description": "置停止标志"}],
                    },
                    {
                        "id": "comparison",
                        "type": "table",
                        "columns": [{"id": "kind", "label": "类型"}],
                        "rows": [{"id": "one", "cells": ["原值"]}],
                    },
                ],
            },
            ensure_ascii=False,
        )
        + "\n```"
    )
    result = mark_unknown_conclusions(original, {"issues": [], "reason": "结论复核未返回有效结构"})
    assert result.startswith(original)
    assert [b.type for _, _, doc in rich_documents(result) if doc for b in doc.blocks] == [
        "step_flow",
        "table",
    ]
    assert "结论复核未返回有效结构" in result
