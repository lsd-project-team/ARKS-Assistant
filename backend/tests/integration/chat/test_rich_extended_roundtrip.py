"""真实 Agent 装配、受认证 HTTP/SSE、资料文件、历史恢复与前端引擎的一体回归。"""

import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.bootstrap import create_app
from app.core.config import AppSettings, ModelSettings
from app.modules.chat.rich_presentation import rich_documents
from tests.helpers.api_paths import project_api
from tests.helpers.models import DeterministicModel

ROOT = Path(__file__).resolve().parents[4]


def events(response):
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    rows = []
    for frame in response.text.replace("\r\n", "\n").split("\n\n"):
        fields = dict(line.split(": ", 1) for line in frame.splitlines() if ": " in line)
        if {"event", "id", "data"} <= fields.keys():
            rows.append(
                {
                    "sequence": int(fields["id"]),
                    "kind": fields["event"],
                    "payload": json.loads(fields["data"]),
                }
            )
    return rows


def test_actual_graph_api_stream_history_files_and_frontend_are_compatible(services, monkeypatch):
    fixture = json.loads(
        (ROOT / "frontend/tests/chat/fixtures/rich-content-extended.json").read_text(
            encoding="utf-8"
        )
    )
    state = {"source_reviews": 0}

    class Model(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **_kwargs):
            if "独立的源码结论复核器" in messages[0].text:
                projected = json.loads(messages[-1].text)["answer"]
                assert "rich-content" not in projected
                assert "| 甲 | 0 |" in projected and "富内容 → 图表" in projected
                state["source_reviews"] += 1
                result = AIMessage(content='{"verdict":"passed","issues":[]}')
            elif any(
                isinstance(row, HumanMessage) and "只用普通Markdown" in row.text
                for row in messages[-2:]
            ):
                result = AIMessage(content="第一轮输入保留为甲0、乙7、丙缺失。")
            elif reads := [
                row
                for row in messages
                if isinstance(row, ToolMessage) and row.name == "read_source"
            ]:
                document = json.loads(json.dumps(fixture))
                document["blocks"][4].update(
                    record_id=state["record"]["id"], version=state["record"]["version"]
                )
                document["blocks"][5]["tool"]["result"] = reads[-1].text[:2000]
                result = AIMessage(content="```rich-content\n" + json.dumps(document) + "\n```")
            else:
                for name in ("chart", "mermaid", "mindmap", "file", "tool_call", "markdown"):
                    assert f"{name}:" in messages[0].text
                result = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "read-entry",
                            "name": "read_source",
                            "args": {"path": "Program.cs", "start_line": 2, "end_line": 2},
                        }
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=result)])

    paths, _, workspace, _, _, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=32768, output_tokens=4096)))
    original = (workspace.root / "Program.cs").read_bytes()
    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    with TestClient(create_app(paths)) as client:
        content = b"isolated attachment\r\n"
        upload = client.post(
            "/api/handover/sources/upload", params={"filename": "验收原文件.txt"}, content=content
        )
        assert upload.status_code == 201, upload.text
        state["record"] = upload.json()
        run_response = client.post(
            project_api(client, "/threads/start"),
            json={
                "content": "读取Program.cs入口；按实际输入甲0、乙7、丙缺失展示图表和分类关系。",
                "source_options": {
                    "use_knowledge": False,
                    "use_memory": False,
                    "use_deepwiki": False,
                },
            },
        )
        assert run_response.status_code == 201
        run = run_response.json()
        rows = events(client.get(project_api(client, f"/runs/{run['id']}/events")))
        assert rows[-1]["kind"] == "done" and rows[-1]["payload"]["status"] == "completed", rows[
            -2:
        ]
        answer = rows[-1]["payload"]["answer"]
        assert all(document is not None for _, _, document in rich_documents(answer))
        assert state["source_reviews"] == 0
        assert not any(row["kind"] == "source_review" for row in rows)
        formats = [row["payload"] for row in rows if row["kind"] == "answer_format_validation"]
        assert formats[-1] == {"passed": True, "blocks": 1, "errors": []}
        assert [row["payload"]["name"] for row in rows if row["kind"] == "tool_start"] == [
            "read_source"
        ]
        assert any(row["kind"] == "answer_validation" and row["payload"]["passed"] for row in rows)
        cursor = rows[len(rows) // 2]["sequence"]
        replay = events(
            client.get(
                project_api(client, f"/runs/{run['id']}/events"),
                headers={"Last-Event-ID": str(cursor)},
            )
        )
        assert replay == [row for row in rows if row["sequence"] > cursor]
        history = client.get(project_api(client, f"/threads/{run['thread_id']}")).json()
        assert history["messages"][-1]["content"] == answer
        source_context = client.get(project_api(client, f"/runs/{run['id']}/context")).json()
        assert source_context["source_evidence"][0]["current_status"] == "match"
        download = client.get(f"/api/handover/sources/{state['record']['id']}/original")
        assert download.status_code == 200 and download.content == content
        report = {"reports": [{"run_id": run["id"], "answer": answer, "context": source_context}]}
        # 只替换供应商；实际前端解析、React Renderer、ECharts 和 Mermaid 都运行。
        rendered = subprocess.run(
            [
                "node",
                "--experimental-strip-types",
                "scripts/verification/rich-content-roundtrip.mjs",
            ],
            cwd=ROOT / "frontend",
            input=json.dumps(report),
            encoding="utf-8",
            capture_output=True,
            timeout=60,
            check=False,
        )
        assert rendered.returncode == 0, rendered.stderr
        result = json.loads(rendered.stdout)
        assert result["reports"][0]["graphics"] == 3 and result["reports"][0]["rendered"]
        assert result["reports"][0]["types"] == [block["type"] for block in fixture["blocks"]]
        second = client.post(
            project_api(client, f"/threads/{run['thread_id']}/runs"),
            json={
                "content": "只用普通Markdown回答第一轮输入，不要结构化。",
                "source_options": {
                    "use_knowledge": False,
                    "use_memory": False,
                    "use_deepwiki": False,
                },
            },
        )
        second.raise_for_status()
        second_rows = events(client.get(project_api(client, f"/runs/{second.json()['id']}/events")))
        assert second_rows[-1]["payload"]["answer"] == "第一轮输入保留为甲0、乙7、丙缺失。"
        restored = client.get(project_api(client, f"/threads/{run['thread_id']}")).json()
        assert len(restored["messages"]) == 4
        assert restored["messages"][1]["content"] == answer
    assert (workspace.root / "Program.cs").read_bytes() == original


def test_frontend_roundtrip_verifier_renders_standard_markdown_mermaid_fence():
    report = {
        "reports": [
            {
                "run_id": "markdown-flow",
                "answer": (
                    "实际主线示意：\n\n```mermaid\nflowchart TD\n A[接收输入] --> B[返回结果]\n```"
                ),
            }
        ]
    }
    rendered = subprocess.run(
        ["node", "--experimental-strip-types", "scripts/verification/rich-content-roundtrip.mjs"],
        cwd=ROOT / "frontend",
        input=json.dumps(report),
        encoding="utf-8",
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert rendered.returncode == 0, rendered.stderr
    assert json.loads(rendered.stdout)["reports"] == [
        {"run_id": "markdown-flow", "types": ["mermaid"], "graphics": 1, "rendered": True}
    ]


def test_source_syntax_repair_keeps_steps_and_version_without_conclusion_review(
    services, monkeypatch
):
    paths, _, workspace, _, _, settings = services
    settings.save(AppSettings(model=ModelSettings(context_tokens=32768, output_tokens=4096)))
    version = workspace.read("Program.cs")["version"]
    good = (
        "入口依据：[Program.cs:2](source:Program.cs#L2)\n\n```rich-content\n"
        + json.dumps(
            {
                "version": 1,
                "blocks": [
                    {
                        "id": "flow",
                        "type": "step_flow",
                        "steps": [
                            {
                                "id": "main",
                                "title": "入口",
                                "description": "Main方法体为空，没有后续动作。",
                                "sources": [
                                    {
                                        "path": "Program.cs",
                                        "start_line": 2,
                                        "end_line": 2,
                                        "version": version,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        )
        + "\n```"
    )
    broken = good.replace("]}\n```", "]\n```")
    calls = {"main": 0, "repair": 0, "review": 0}

    class Model(DeterministicModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if "独立的源码结论复核器" in messages[0].text:
                calls["review"] += 1
                raise AssertionError("源码回答不能再调用结论复核")
            calls["main"] += 1
            if any(
                isinstance(row, HumanMessage) and row.text.startswith("系统展示语法校验")
                for row in messages
            ):
                calls["repair"] += 1
                result = AIMessage(content=good)
            elif any(
                isinstance(row, ToolMessage) and row.name == "read_source" for row in messages
            ):
                result = AIMessage(content=broken)
            else:
                result = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "read-main",
                            "name": "read_source",
                            "args": {"path": "Program.cs", "start_line": 2, "end_line": 2},
                        }
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=result)])

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", lambda *_a, **_k: Model())
    with TestClient(create_app(paths)) as client:
        created = client.post(
            project_api(client, "/threads/start"),
            json={
                "content": "Program.cs的入口步骤",
                "source_options": {
                    "use_knowledge": False,
                    "use_memory": False,
                    "use_deepwiki": False,
                },
            },
        )
        assert created.status_code == 201
        run = created.json()
        rows = events(client.get(project_api(client, f"/runs/{run['id']}/events")))
        assert rows[-1]["payload"]["status"] == "completed"
        assert rows[-1]["payload"]["answer"] == good
        assert calls == {"main": 3, "repair": 1, "review": 0}
        assert [
            row["payload"]["passed"] for row in rows if row["kind"] == "answer_format_validation"
        ] == [False, True]
        assert not any(row["kind"] == "source_review" for row in rows)
        assert [row["payload"]["name"] for row in rows if row["kind"] == "tool_start"] == [
            "read_source"
        ]
        document = list(rich_documents(good))[0][2]
        assert document.blocks[0].steps[0].sources[0].version == version
        history = client.get(project_api(client, f"/threads/{run['thread_id']}")).json()
        assert len(history["messages"]) == 2 and history["messages"][-1]["content"] == good
        assert all("系统展示语法校验" not in row["content"] for row in history["messages"])
