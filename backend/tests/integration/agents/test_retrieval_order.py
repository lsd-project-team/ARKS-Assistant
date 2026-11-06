"""实际图与工具组合：按需选源，依据足够时停止，回答后不再来源复核。"""

import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.semantic import SemanticRetrieval
from app.modules.source_analysis.evidence import SourceEvidence, source_excerpt
from tests.helpers.models import DeterministicModel


@pytest.mark.parametrize(
    "route",
    [
        "experience",
        "regenerated-experience",
        "unused-source",
        "source",
        "mixed",
        "mixed-unavailable-context",
        "fallback",
    ],
)
async def test_selected_basis_controls_retrieval_without_post_generation_review(
    services, monkeypatch, route
):
    paths, database, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=32768, output_tokens=2048)))
    monkeypatch.setattr(SemanticRetrieval, "scores", lambda _s, _q, docs: dict.fromkeys(docs, 1))
    saved = DebugIssues(HandoverStore(database=database)).save(
        DebugWrite(
            title="蓝膜刺穿处理经验",
            payload={
                "question": "蓝膜穿孔如何解决？",
                "answer": "0.6×0.45mm芯片、原025/050顶针改用075，"
                "焊头力20～30g、速度3mm/s、高度280～300（单位未标）。",
                "keywords": ["蓝膜", "顶针"],
            },
        ),
        {},
    )
    reference = f"[蓝膜刺穿处理经验](debug-issue:{saved['id']}/1)"
    experience = (
        "同类0.6×0.45mm芯片可参考075顶针，焊头力20～30g、速度3mm/s、高度280～300（单位未标）。"
        + reference
    )
    source = "Main入口为空。[Program.cs:2](source:Program.cs#L2)"
    expected = {
        "experience": experience,
        "regenerated-experience": experience,
        "unused-source": experience,
        "source": source,
        "mixed": source + "\n\n" + experience,
        "mixed-unavailable-context": source + "\n\n" + experience,
        "fallback": source,
    }[route]
    questions = {
        "experience": "已经降低顶针高度、速度和焊头力，蓝膜仍然刺穿，下一步怎么处理？",
        "regenerated-experience": "蓝膜刺穿怎么处理？",
        "unused-source": "蓝膜怎么处理？有用的经验即可。",
        "source": "解释Program.cs入口",
        "mixed": "解释Program.cs入口，并给蓝膜处理经验",
        "mixed-unavailable-context": "解释Program.cs入口，并给蓝膜处理经验",
        "fallback": "经验中找不到入口说明时，请读取Program.cs解释入口",
    }
    checks = []

    def forbidden_reference_check(*_args, **_kwargs):
        pytest.fail("回答生成后不能再检查源码引用")

    monkeypatch.setattr(SourceEvidence, "check", forbidden_reference_check)
    if route == "mixed-unavailable-context":

        def unavailable(*_args):
            raise ValueError("复核上下文超限")

        monkeypatch.setattr(
            "app.modules.source_analysis.review_context.source_review_context", unavailable
        )

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            prompt = messages[0].text
            if "你只负责筛选资料" in prompt:
                if route == "fallback":
                    return ChatResult(
                        generations=[
                            ChatGeneration(
                                message=AIMessage(content='{"scope":"records","selections":[]}')
                            )
                        ]
                    )
                return super()._generate(messages, *args, **kwargs)
            if "你负责核查历史经验回答" in prompt:
                payload = json.loads(messages[-1].text)
                checks.append(payload)
                if route == "mixed":
                    block = payload["source_context"]["source"][0]
                    assert block["path"] == "Program.cs"
                    assert block["version"] == workspace.read("Program.cs")["version"]
                    assert any("Main" in row["text"] for row in block["lines"])
                if route == "mixed-unavailable-context":
                    assert payload["source_context"] == {
                        "source": [],
                        "source_omissions": [{"reason": "unavailable"}],
                    }
                return super()._generate(messages, *args, **kwargs)
            tools = [row.name for row in messages if isinstance(row, ToolMessage)]
            if route in {"experience", "regenerated-experience"}:
                assert "【源码核查】" not in prompt
            if route != "source" and "search_debug_issues" not in tools:
                call = {
                    "id": "knowledge",
                    "name": "search_debug_issues",
                    "args": {"query": "蓝膜处理经验"},
                }
            elif (
                route not in {"experience", "regenerated-experience"} and "read_source" not in tools
            ):
                call = {
                    "id": "source",
                    "name": "read_source",
                    "args": {"path": "Program.cs", "start_line": 2, "end_line": 2},
                }
            else:
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=expected))])
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="", tool_calls=[call]))]
            )

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    options = {"use_memory": False, "use_knowledge": True, "use_deepwiki": False}
    run = repository.create_run(None, questions[route], [], options)
    if route == "regenerated-experience":
        previous = SourceEvidence(
            workspace, lambda kind, row: repository.event(run["id"], kind, row)
        )
        previous.record(source_excerpt(workspace, "Program.cs", 2, 2))
        repository.finish(run["id"], experience)
        run = repository.regenerate(run["id"])
    events = []
    try:
        answer = await runtime.execute(run, lambda *row: events.append(row))
        assert answer == expected
        calls = [row["name"] for kind, row in events if kind == "tool_start"]
        assert (
            calls
            == {
                "experience": ["search_debug_issues"],
                "regenerated-experience": ["search_debug_issues"],
                "unused-source": ["search_debug_issues", "read_source"],
                "source": ["read_source"],
                "mixed": ["search_debug_issues", "read_source"],
                "mixed-unavailable-context": ["search_debug_issues", "read_source"],
                "fallback": ["search_debug_issues", "read_source"],
            }[route]
        )
        assert checks == []
        assert not {"answer_validation", "knowledge_answer_review", "answer_review_note"} & {
            kind for kind, _ in events
        }
        assert any(kind == "token" for kind, _ in events)
        assert not any("系统引用核对结果" in str(row) for row in checks)
    finally:
        runtime.semantic.close()
