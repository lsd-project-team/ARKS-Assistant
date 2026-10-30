"""显式复测 ARKS 经验图文：使用截图案例的隔离副本，不读取或写入正式会话。"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from rich_content_roundtrip import ROOT, TestClient, assert_roundtrip, create_app

from app.core.config import Paths, SettingsStore
from app.modules.auth.models import Account
from app.modules.chat.rich_presentation import project_rich_content

OPTIONS = {"use_memory": False, "use_knowledge": True, "use_deepwiki": False}
VISUALS = {"mermaid", "diagram", "mindmap", "step_flow"}


def verify(args):
    # 只把供应商配置放在内存，不复制密钥、正式账号、原始会话或知识数据库。
    config = (
        SettingsStore(Paths(args.settings_data))
        .load()
        .model_copy(
            update={"mcp_servers": [], "auto_memory": False, "deepwiki_repo": ""},
            deep=True,
        )
    )
    reports = []
    if not config.model.api_key or not config.model.model:
        raise ValueError("当前供应商配置不完整，无法执行真实模型验收")
    fixture = json.loads(
        (ROOT / "backend/tests/fixtures/knowledge/blue-film-rich.json").read_text(encoding="utf-8")
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="arks-rich-knowledge-") as temporary:
        directory = Path(temporary)
        source = directory / "source"
        source.mkdir()
        app = create_app(Paths(directory / "data", source))
        app.state.projects.base.settings.load = lambda: config.model_copy(deep=True)
        try:
            with TestClient(app) as client:
                auth = app.state.auth
                with auth.database.session.begin() as session:
                    session.add(
                        Account(
                            username="arks-rich-test",
                            display_name="隔离业务图文验收",
                            role="user",
                            password_hash=auth.hasher.hash("isolated-arks-rich-only"),
                        )
                    )
                login = client.post(
                    "/api/auth/login",
                    json={
                        "username": "arks-rich-test",
                        "password": "isolated-arks-rich-only",
                    },
                )
                login.raise_for_status()
                client.headers["X-Arks-CSRF"] = login.json()["csrf_token"]
                record = client.post("/api/handover/debug-issues", json=fixture)
                assert record.status_code == 201, record.text
                reference = f"debug-issue:{record.json()['id']}/1"
                assert not record.json()["payload"]["metadata"].get("images")
                project = client.get("/api/projects").json()["default_project_id"]
                root = f"/api/p/{project}"
                thread_id = None
                questions = [
                    "蓝膜穿孔如何解决用图文并茂告诉我",
                    "把上面的组合方案用流程图展示，保留适用条件、单位待确认和原经验引用。",
                ]
                for question in questions:
                    report = assert_roundtrip(
                        client,
                        root,
                        question,
                        set(),
                        thread_id,
                        reports,
                        source_options=OPTIONS,
                    )
                    thread_id = report["thread_id"]
                    checks = [
                        event["payload"]
                        for event in report["events"]
                        if event["kind"] == "knowledge_answer_review"
                    ]
                    assert checks and checks[-1]["verdict"] in {"passed", "revised"}, checks
                    assert reference in report["answer"]
                    assert VISUALS.intersection(report["types"]), report["answer"]
                    prose = "".join(project_rich_content(report["answer"]).split()).replace(
                        "~", "～"
                    )
                    assert all(
                        text in prose
                        for text in ("0.6×0.45mm", "075", "20～30g", "3mm/s", "280～300", "216")
                    ), prose
                    assert "单位" in prose and ("确认" in prose or "未明确" in prose)
                    print(
                        f"ARKS经验图文通过：{report['types']}，核查{checks[-1]['verdict']}，"
                        f"历史{report['history_messages']}条",
                        flush=True,
                    )
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
                assert all(row["rendered"] for row in frontend["reports"])
                (args.output.parent / "frontend.json").write_text(
                    json.dumps(frontend, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print("两轮真实回答的前端解析和图形渲染通过", flush=True)
        finally:
            args.output.write_text(
                json.dumps(
                    {"model": config.model.model, "reports": reports},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--settings-data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/arks-rich-content/live.json")
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not args.output.is_relative_to(ROOT / "output"):
        parser.error("报告只能写入当前工作树的output目录")
    verify(args)
