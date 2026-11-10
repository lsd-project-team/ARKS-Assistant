"""显式真实ARKS源码验收：只读业务源码，独立账号/数据库，复测取片步骤及流程图。"""

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from rich_content_roundtrip import ROOT, TestClient, assert_roundtrip, create_app

from app.core.config import Paths, SettingsStore
from app.modules.auth.models import Account
from app.modules.source_analysis.workspace import Workspace

OPTIONS = {"use_memory": False, "use_knowledge": False, "use_deepwiki": False}


def verify(args):
    config = (
        SettingsStore(Paths(args.settings_data))
        .load()
        .model_copy(
            update={"mcp_servers": [], "auto_memory": False, "deepwiki_repo": ""}, deep=True
        )
    )
    if not config.model.api_key or not config.model.model:
        raise ValueError("当前供应商配置不完整")
    source = Workspace(args.source_root)
    # 运行仅允许读源码；对实际可访问C#文本取指纹，避免把未改动当作口头保证。
    fingerprints = {
        source.relative(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.files()
        if path.suffix.lower() == ".cs"
    }
    reports = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="arks-source-steps-") as temporary:
        app = create_app(Paths(Path(temporary) / "data", source.root))
        app.state.projects.base.settings.load = lambda: config.model_copy(deep=True)
        try:
            with TestClient(app) as client:
                auth = app.state.auth
                with auth.database.session.begin() as session:
                    session.add(
                        Account(
                            username="source-steps-test",
                            display_name="源码步骤隔离验收",
                            role="user",
                            password_hash=auth.hasher.hash("isolated-source-steps-only"),
                        )
                    )
                login = client.post(
                    "/api/auth/login",
                    json={
                        "username": "source-steps-test",
                        "password": "isolated-source-steps-only",
                    },
                )
                login.raise_for_status()
                client.headers["X-Arks-CSRF"] = login.json()["csrf_token"]
                root = f"/api/p/{client.get('/api/projects').json()['default_project_id']}"
                seed = assert_roundtrip(
                    client,
                    root,
                    "先只回复“收到”：我刚才在讨论蓝膜刺穿经验。",
                    set(),
                    source_options=OPTIONS,
                )
                thread_id = seed["thread_id"]
                for question, expected in [
                    ("取片的步骤", set()),
                    (
                        "用流程图展示正常生产取片，标出漏晶检测后的重新检测、退出、忽略、重取和下一颗分支。不要重复整份文字步骤。",
                        set(),
                    ),
                ]:
                    report = assert_roundtrip(
                        client, root, question, expected, thread_id, reports, source_options=OPTIONS
                    )
                    if "流程图" in question:
                        assert "mermaid" in report["types"] or re.search(
                            r"(?m)^`{3,}mermaid\s*$", report["answer"]
                        ), "须输出可渲染流程图"
                    assert not any(event["kind"] == "source_review" for event in report["events"])
                    assert not any(
                        event["kind"] == "provider_usage"
                        and event["payload"].get("purpose") == "source_verification"
                        for event in report["events"]
                    )
                    assert "结论复核提示" not in report["answer"]
                    validation = [
                        event["payload"]
                        for event in report["events"]
                        if event["kind"] == "answer_validation"
                    ]
                    assert validation and validation[-1]["passed"], validation
                    assert any(
                        "PickActionNode" in row["path"]
                        for row in report["context"]["source_evidence"]
                    ), "不能把底层或旧实现当成正常生产入口"
                    assert "蓝膜" not in report["answer"], "新问题没有要求关联历史故障"
                    assert report["context"].get("source_review") is None
                    print(
                        f"真实源码问答通过：{report['types']}，引用{len(validation[-1]['citations'])}项，历史{report['history_messages']}条",
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
                assert len(frontend["reports"]) == len(reports)
                assert all(row["rendered"] for row in frontend["reports"])
                (args.output.parent / "frontend.json").write_text(
                    json.dumps(frontend, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        finally:
            unchanged = all(
                hashlib.sha256((source.root / path).read_bytes()).hexdigest() == version
                for path, version in fingerprints.items()
            )
            args.output.write_text(
                json.dumps(
                    {
                        "model": config.model.model,
                        "source_unchanged": unchanged,
                        "source_files": len(fingerprints),
                        "reports": reports,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            assert unchanged, "业务源码指纹发生变化"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--settings-data", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/arks-source-steps/live.json")
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not args.output.is_relative_to(ROOT / "output") or args.output.exists():
        parser.error("报告须写入output下的新文件，不能覆盖既有结果")
    verify(args)
