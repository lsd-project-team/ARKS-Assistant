import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus
from tests.helpers.models import DeterministicModel


@pytest.mark.parametrize("via_tool", [False, True])
async def test_final_revision_is_persisted_without_review_json_streaming(
    services, monkeypatch, via_tool
):
    paths, database, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(model=ModelSettings(context_tokens=16384, output_tokens=1024), mcp_servers=[])
    )
    issues = DebugIssues(HandoverStore(database=database))
    saved = issues.save(
        DebugWrite(title="蓝膜刺穿经验", payload={"problem": "组合调整后216颗无刺穿。"}), {}
    )
    issues.save(DebugWrite(title="通信故障X778", payload={"problem": "不应发送的其他记录"}), {})
    reviewed = []
    reference = f"[蓝膜刺穿经验 · v1](debug-issue:{saved['id']}/1)"
    revision = "本次组合调整后216颗无刺穿，记录不足以证明长期根治。" + reference

    class Model(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if "你负责复核并修订基于历史经验" in messages[0].text:
                payload = json.loads(messages[-1].text)
                reviewed.append(payload)
                passed = payload["answer"] == revision
                answer = AIMessage(
                    content=json.dumps(
                        {
                            "verdict": "passed" if passed else "revised",
                            "reason": "保留试验边界",
                            "answer": "" if passed else revision,
                        }
                    )
                )
            elif via_tool and not any(isinstance(row, ToolMessage) for row in messages):
                answer = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "read_debug_issue",
                            "args": {"record_id": saved["id"]},
                            "id": "read",
                        }
                    ],
                )
            else:
                answer = AIMessage(content="任何工况都能根治。" + reference)
            return ChatResult(generations=[ChatGeneration(message=answer)])

    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_args, **_kwargs: Model()
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    options = {"use_memory": False, "use_knowledge": True, "use_deepwiki": False}
    query = "请读取经验编号" if via_tool else "蓝膜刺穿经验"
    run = repository.create_run(None, query, [], options)
    events = []
    answer = await runtime.execute(run, lambda *event: events.append(event))
    repository.finish(run["id"], answer)
    assert answer == revision
    assert repository.thread(run["thread_id"])["messages"][-1]["content"] == revision
    assert len(reviewed) == 2
    assert all(
        [row["reference"] for row in payload["records"]] == [reference] for payload in reviewed
    )
    assert "不应发送的其他记录" not in str(reviewed)
    assert not any('"verdict"' in payload["text"] for kind, payload in events if kind == "token")
    assert any(kind == "answer_replace" and row["text"] == revision for kind, row in events)
    assert issues.store.get(saved["id"])["payload"]["original_text"] == "组合调整后216颗无刺穿。"


def test_review_context_rejects_unknown_or_wrong_version_references(services):
    store = HandoverStore(database=services[1])
    saved = DebugIssues(store).save(
        DebugWrite(title="范围测试", payload={"problem": "原始事实"}), {}
    )
    corpus = DebugIssueCorpus(services[1])
    assert corpus.review_records({saved["id"]: 2, "unknown": 1}) == []
    records = corpus.review_records({saved["id"]: 1})
    assert len(records) == 1 and records[0]["content"]["记录正文"] == "原始事实"
    assert "compatibility" in records[0]
