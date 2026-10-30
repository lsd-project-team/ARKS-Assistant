"""ARKS经验完整链路：筛选、富内容事实修订、SSE、历史及实际前端图形渲染。"""

import json
import subprocess

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.bootstrap import create_app
from app.core.config import AppSettings, ModelSettings
from app.modules.chat.rich_presentation import rich_documents
from app.modules.knowledge.corpora.debug_issues import ANSWER_GUIDANCE
from tests.helpers.api_paths import project_api
from tests.helpers.models import DeterministicModel
from tests.integration.chat.test_rich_extended_roundtrip import ROOT, events


def document(reference, *, wrong_unit=False):
    height = "280～300μm" if wrong_unit else "280～300（单位待确认）"
    return (
        "适用于0.6×0.45mm芯片、原用025/050顶针的蓝膜取片工况。\n\n```rich-content\n"
        + json.dumps(
            {
                "version": 1,
                "blocks": [
                    {
                        "id": "solution",
                        "type": "mermaid",
                        "title": "经验方案示意，非操作先后顺序",
                        "content": (
                            "flowchart TD\n A[组合调整] --> B[075顶针]\n"
                            " A --> C[焊头力20～30g]\n A --> D[顶针速度3mm/s]\n"
                            " A --> E[顶针高度单位待确认]"
                        ),
                    },
                    {
                        "id": "parameters",
                        "type": "table",
                        "columns": [
                            {"id": "name", "label": "参数"},
                            {"id": "value", "label": "值"},
                        ],
                        "rows": [{"id": "height", "cells": ["顶针高度", height]}],
                    },
                    {
                        "id": "result",
                        "type": "markdown",
                        "content": "这组调整曾连续取放216颗无刺穿，不能认定某一项单独有效。"
                        + reference,
                    },
                ],
            },
            ensure_ascii=False,
        )
        + "\n```"
    )


def test_arks_knowledge_fact_revision_preserves_graphics_citations_and_roundtrip(
    services, monkeypatch
):
    state = {"checks": []}

    class Model(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            prompt = messages[0].text
            if "你负责核查历史经验回答" in prompt:
                # 供应商边界替身只判定明确的单位错误，筛选和保存仍走真实实现。
                assert "记录没有原图或image_count=0" in prompt
                assert "mermaid:" in prompt and "外层仍只返回核查JSON对象" in prompt
                payload = json.loads(messages[-1].text)
                state["checks"].append(payload)
                assert payload["record_context"][0]["image_count"] == 0
                if "rich-content" in payload["answer"]:
                    assert "rich-content" not in payload["answer_text"]
                    assert "组合调整" in payload["answer_text"]
                    assert (
                        "280～300μm" in payload["answer_text"]
                        or "单位待确认" in payload["answer_text"]
                    )
                bad = "280～300μm" in payload["answer"]
                result = AIMessage(
                    content=json.dumps(
                        {
                            "verdict": "revised" if bad else "passed",
                            "reason": "高度单位无依据" if bad else "参数及示意有据",
                            "answer": document(state["reference"]) if bad else "",
                        }
                    )
                )
            elif "你只负责筛选资料" in prompt:
                return super()._generate(messages, stop, run_manager, **kwargs)
            elif any(
                isinstance(row, HumanMessage) and "只用普通Markdown" in row.text
                for row in messages[-2:]
            ):
                result = AIMessage(
                    content="顶针高度280～300，单位需要先确认。" + state["reference"]
                )
            elif any(
                isinstance(row, ToolMessage) and row.name == "search_debug_issues"
                for row in messages
            ):
                result = AIMessage(content=document(state["reference"], wrong_unit=True))
            else:
                assert "没有历史原图也可以生成有依据的示意图" in ANSWER_GUIDANCE
                assert "图文并茂" in prompt
                result = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "find-blue-film",
                            "name": "search_debug_issues",
                            "args": {"query": "蓝膜刺穿"},
                        }
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=result)])

    paths, _, _, _, _, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=32768, output_tokens=4096)))
    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    fixture = json.loads(
        (ROOT / "backend/tests/fixtures/knowledge/blue-film-rich.json").read_text(encoding="utf-8")
    )
    options = {"use_memory": False, "use_knowledge": True, "use_deepwiki": False}
    with TestClient(create_app(paths)) as client:
        saved = client.post("/api/handover/debug-issues", json=fixture)
        assert saved.status_code == 201, saved.text
        state["reference"] = f"[蓝膜刺穿处理经验](debug-issue:{saved.json()['id']}/1)"
        created = client.post(
            project_api(client, "/threads/start"),
            json={"content": "蓝膜穿孔如何解决用图文并茂告诉我", "source_options": options},
        )
        assert created.status_code == 201
        run = created.json()
        rows = events(client.get(project_api(client, f"/runs/{run['id']}/events")))
        assert rows[-1]["kind"] == "done" and rows[-1]["payload"]["status"] == "completed"
        answer = rows[-1]["payload"]["answer"]
        assert answer == document(state["reference"])
        assert "μm" not in answer and state["reference"] in answer
        blocks = [block for _, _, doc in rich_documents(answer) for block in doc.blocks]
        assert [(block.id, block.type) for block in blocks] == [
            ("solution", "mermaid"),
            ("parameters", "table"),
            ("result", "markdown"),
        ]
        assert len(state["checks"]) == 2 and state["checks"][-1]["final_check"]
        assert state["checks"][0]["records"] == state["checks"][1]["records"]
        assert (
            next(row["payload"] for row in rows if row["kind"] == "knowledge_answer_review")[
                "verdict"
            ]
            == "revised"
        )
        assert next(row["payload"] for row in rows if row["kind"] == "answer_format_validation")[
            "passed"
        ]
        cursor = rows[len(rows) // 2]["sequence"]
        replay = events(
            client.get(
                project_api(client, f"/runs/{run['id']}/events"),
                headers={"Last-Event-ID": str(cursor)},
            )
        )
        assert replay == [row for row in rows if row["sequence"] > cursor]
        restored = client.get(project_api(client, f"/threads/{run['thread_id']}")).json()
        assert restored["messages"][-1]["content"] == answer
        second = client.post(
            project_api(client, f"/threads/{run['thread_id']}/runs"),
            json={
                "content": "只用普通Markdown回答高度与单位，不要图形。",
                "source_options": options,
            },
        )
        assert second.status_code == 201
        second_events = events(
            client.get(project_api(client, f"/runs/{second.json()['id']}/events"))
        )
        assert (
            second_events[-1]["payload"]["answer"]
            == "顶针高度280～300，单位需要先确认。" + state["reference"]
        )
        history = client.get(project_api(client, f"/threads/{run['thread_id']}")).json()
        assert len(history["messages"]) == 4 and history["messages"][1]["content"] == answer
        rendered = subprocess.run(
            [
                "node",
                "--experimental-strip-types",
                "scripts/verification/rich-content-roundtrip.mjs",
            ],
            cwd=ROOT / "frontend",
            input=json.dumps({"reports": [{"run_id": run["id"], "answer": answer}]}),
            encoding="utf-8",
            capture_output=True,
            timeout=60,
            check=False,
        )
        assert rendered.returncode == 0, rendered.stderr
        assert json.loads(rendered.stdout)["reports"][0] == {
            "run_id": run["id"],
            "types": ["mermaid", "table", "markdown"],
            "graphics": 1,
            "rendered": True,
        }
