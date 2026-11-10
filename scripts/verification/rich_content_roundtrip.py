"""显式真实模型验收：临时账号/源码/资料，经现有 HTTP、SSE 和历史恢复验证富内容。"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.bootstrap import create_app  # noqa: E402
from app.core.config import Paths, SettingsStore  # noqa: E402
from app.modules.auth.models import Account  # noqa: E402
from app.modules.chat.rich_presentation import rich_documents  # noqa: E402


def sse_events(response):
    """按既有 SSE 字段读取，不添加专用富内容事件。"""
    response.raise_for_status()
    assert response.headers["content-type"].startswith("text/event-stream")
    for frame in response.text.replace("\r\n", "\n").split("\n\n"):
        fields = dict(line.split(": ", 1) for line in frame.splitlines() if ": " in line)
        if {"id", "event", "data"} <= fields.keys():
            yield {
                "sequence": int(fields["id"]),
                "kind": fields["event"],
                "payload": json.loads(fields["data"]),
            }


def assert_roundtrip(
    client, root, question, expected, thread_id=None, sink=None, *, source_options=None
):
    endpoint = f"{root}/threads/{thread_id}/runs" if thread_id else f"{root}/threads/start"
    response = client.post(
        endpoint,
        json={
            "content": question,
            "source_options": source_options
            or {"use_memory": False, "use_knowledge": False, "use_deepwiki": False},
        },
    )
    response.raise_for_status()
    assert response.status_code == 201
    run = response.json()
    events = list(sse_events(client.get(f"{root}/runs/{run['id']}/events")))
    assert events and events[-1]["kind"] == "done"
    assert events[-1]["payload"]["status"] == "completed", events[-2:]
    answer = events[-1]["payload"]["answer"]
    ids = [event["sequence"] for event in events]
    assert ids == sorted(set(ids))
    cursor = ids[len(ids) // 2]
    replay = list(
        sse_events(
            client.get(f"{root}/runs/{run['id']}/events", headers={"Last-Event-ID": str(cursor)})
        )
    )
    assert replay == [event for event in events if event["sequence"] > cursor]
    history = client.get(f"{root}/threads/{run['thread_id']}").json()
    assert history["messages"][-1]["content"] == answer
    assert history["runs"][-1]["answer"] == answer
    documents = [document for _, _, document in rich_documents(answer)]
    blocks = [block for document in documents if document for block in document.blocks]
    context = client.get(f"{root}/runs/{run['id']}/context")
    context.raise_for_status()
    report = {
        "question": question,
        "answer": answer,
        "run_id": run["id"],
        "context": context.json(),
        "thread_id": run["thread_id"],
        "events": events,
        "types": [block.type for block in blocks],
        "history_messages": len(history["messages"]),
    }
    if sink is not None:
        sink.append(report)
    validations = [
        event["payload"] for event in events if event["kind"] == "answer_format_validation"
    ]
    assert validations and validations[-1]["passed"], {"validation": validations, "answer": answer}
    assert all(document is not None for document in documents), answer
    assert expected <= {block.type for block in blocks}, answer
    return report


def verify(output):
    config = (
        SettingsStore(Paths())
        .load()
        .model_copy(
            update={"mcp_servers": [], "auto_memory": False, "deepwiki_repo": ""}, deep=True
        )
    )
    if not config.model.api_key or not config.model.model:
        raise ValueError("当前供应商配置不完整，无法进行真实模型验收")
    reports = []
    with tempfile.TemporaryDirectory(prefix="arks-rich-roundtrip-") as temporary:
        directory = Path(temporary)
        source = directory / "source"
        source.mkdir()
        code = "class Program {\n static void Main() {}\n}\n"
        (source / "Program.cs").write_text(code, encoding="utf-8")
        app = create_app(Paths(directory / "data", source))
        # 密钥只保存在内存，不复制正式配置/账号/历史，也不写入报告。
        app.state.projects.base.settings.load = lambda: config.model_copy(deep=True)
        with TestClient(app) as client:
            auth = app.state.auth
            with auth.database.session.begin() as session:
                session.add(
                    Account(
                        username="rich-roundtrip",
                        display_name="富内容端到端验收",
                        role="user",
                        password_hash=auth.hasher.hash("isolated-rich-only"),
                    )
                )
            login = client.post(
                "/api/auth/login",
                json={"username": "rich-roundtrip", "password": "isolated-rich-only"},
            )
            login.raise_for_status()
            client.headers["X-Arks-CSRF"] = login.json()["csrf_token"]
            projects = client.get("/api/projects").json()
            root = f"/api/p/{projects['default_project_id']}"
            uploaded = client.post(
                "/api/handover/sources/upload",
                params={"filename": "验收.txt"},
                content="临时验收原文件，非正式资料。".encode(),
            )
            uploaded.raise_for_status()
            record = uploaded.json()
            questions = [
                (
                    "请用应用支持的柱状图组件展示我提供的测试输入：甲=0、乙=7、丙缺失。"
                    "保留缺失，不补零；直接显示图表，不给绘图代码或JSON示例。",
                    {"chart"},
                ),
                (
                    "接着用应用支持的流程图组件描述接收输入、检查数据、显示内容三个步骤的关系，"
                    "再用思维导图组件展示富内容下面分为Markdown和图表的树状分类。"
                    "直接展示两种图，不给代码示例。",
                    {"mermaid", "mindmap"},
                ),
                (
                    "请先读取Program.cs，说明Main方法实际做了什么，并用源码引用卡片附已读行号。"
                    f"同时展示已上传的资料文件卡片：record_id={record['id']}，"
                    f"文件名=验收.txt，version={record['version']}。不要声称修改了文件。",
                    {"file", "source_reference"},
                ),
            ]
            try:
                thread_id = None
                for index, (question, expected) in enumerate(questions, 1):
                    report = assert_roundtrip(client, root, question, expected, thread_id, reports)
                    thread_id = report["thread_id"]
                    if index == 1:
                        blocks = [
                            b for _, _, d in rich_documents(report["answer"]) for b in d.blocks
                        ]
                        chart = next(block for block in blocks if block.type == "chart")
                        assert chart.labels == ["甲", "乙", "丙"]
                        assert chart.series[0].values == [0, 7, None]
                    if index == 3:
                        assert any(e["kind"] == "tool_end" for e in report["events"])
                        validations = [
                            e["payload"]
                            for e in report["events"]
                            if e["kind"] == "answer_validation"
                        ]
                        assert validations and validations[-1]["passed"]
                        assert client.get(
                            f"/api/handover/sources/{record['id']}/original"
                        ).content == ("临时验收原文件，非正式资料。".encode())
                    print(
                        f"真实场景 {index} 通过：{report['types']}，"
                        f"历史恢复 {report['history_messages']} 条消息",
                        flush=True,
                    )
                assert (source / "Program.cs").read_text(encoding="utf-8") == code
                rendered = subprocess.run(
                    [
                        "node",
                        "--experimental-strip-types",
                        "scripts/verification/rich-content-roundtrip.mjs",
                    ],
                    cwd=ROOT / "frontend",
                    input=json.dumps({"reports": reports}),
                    encoding="utf-8",
                    capture_output=True,
                    timeout=60,
                    check=False,
                )
                assert rendered.returncode == 0, rendered.stderr
                frontend = json.loads(rendered.stdout)
                assert all(item["rendered"] for item in frontend["reports"])
                print("真实回答已通过前端 Renderer、ECharts 与 Mermaid 实际渲染", flush=True)
                (output.parent / "frontend.json").write_text(
                    json.dumps(frontend, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            finally:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(
                    json.dumps(
                        {"model": config.model.model, "reports": reports},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="显式使用当前供应商并消耗额度")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "output/rich-content-roundtrip/live.json"
    )
    args = parser.parse_args()
    if not args.live:
        parser.error("真实模型验收必须显式指定 --live")
    if not args.output.resolve().is_relative_to(ROOT / "output"):
        parser.error("报告只能保存在 output 子目录")
    verify(args.output.resolve())
