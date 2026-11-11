"""使用当前 ARKS 的真实模型和已登记 MCP，在独立账号和数据库中验收参数问答。"""

import argparse
import json
import re
import tempfile
from hashlib import sha256
from pathlib import Path

from rich_content_roundtrip import ROOT, TestClient, assert_roundtrip, create_app

from app.core.config import Paths, SettingsStore
from app.modules.auth.models import Account

SERVER_ID = "parameter_reuse"
TOOL_NAME = f"mcp_{SERVER_ID}_lookup"
CASES = (
    ("芯片尺寸能不能从旧设备直接复用到新设备？", 4, ("ComponentSize", "配方共用", "下发")),
    ("点胶针偏移能直接复用吗？", 94, ("DispensingNeedleOffset", "坐标", "保护")),
    ("点胶时正压能不能直接复用？", 344, ("DispensePressure", "未登记", "不能确认")),
    ("纠偏视觉延时能直接复用吗？", 47, ("AdjustVisionDelay", "不一致", "不能确认")),
    ("芯片晶圆中心能直接复用吗？", 34, ("ComponentWaferCenter", "未找到", "不能确认")),
    ("设备端编辑状态 EditState 能直接复用吗？我还不知道是哪一个库。", None, ("EditState", "库")),
    ("ZX2200 的 GluerPressureTestV99 能直接复用吗？", None, ("GluerPressureTestV99", "清单")),
    (
        "点胶相关参数整体能直接复用吗？说下清单里的总数，举两项有代表性的并给原表依据。",
        None,
        ("62", "59", "工艺确认清单"),
    ),
)


def verify(args):
    settings = SettingsStore(Paths(args.settings_data)).load()
    if not settings.model.api_key or not settings.model.model:
        raise ValueError("当前供应商配置不完整")
    server = next(server for server in settings.mcp_servers if server.id == SERVER_ID)
    workbook = Path(server.args[server.args.index("--workbook") + 1])
    source_digest = sha256(workbook.read_bytes()).hexdigest()
    config = settings.model_copy(
        update={"mcp_servers": [server], "auto_memory": False, "deepwiki_repo": ""}, deep=True
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    reports = []
    try:
        with tempfile.TemporaryDirectory(prefix="arks-parameter-mcp-") as temporary:
            folder = Path(temporary)
            source = folder / "empty-source"
            source.mkdir()
            paths = Paths(folder / "data", source)
            SettingsStore(paths).save(config)
            app = create_app(paths)
            with TestClient(app) as client:
                run_cases(client, app.state.auth, reports)
    finally:
        unchanged = sha256(workbook.read_bytes()).hexdigest() == source_digest
        args.output.write_text(
            json.dumps(
                {
                    "model": config.model.model,
                    "workbook_sha256": source_digest,
                    "workbook_unchanged": unchanged,
                    "reports": reports,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        assert unchanged, "验收前后的工作簿指纹不同"
    assert all(report["passed"] for report in reports), "存在未通过的真实问答，请查验收报告"


def run_cases(client, auth, reports):
    username, password = "parameter-mcp-test", "isolated-parameter-mcp-only"
    with auth.database.session.begin() as session:
        session.add(
            Account(
                username=username,
                display_name="参数 MCP 验收",
                role="admin",
                password_hash=auth.hasher.hash(password),
            )
        )
    login = client.post("/api/auth/login", json={"username": username, "password": password})
    login.raise_for_status()
    client.headers["X-Arks-CSRF"] = login.json()["csrf_token"]
    probe = client.post(f"/api/mcp/{SERVER_ID}/probe")
    probe.raise_for_status()
    assert [tool["name"] for tool in probe.json()["tools"]] == ["lookup"]
    root = f"/api/p/{client.get('/api/projects').json()['default_project_id']}"
    for question, row, terms in CASES:
        report = assert_roundtrip(client, root, question, set(), sink=reports)
        report["passed"] = False
        answer = report["answer"]
        calls = [event["payload"] for event in report["events"] if event["kind"] == "tool_end"]
        correct_tool = any(
            call["name"] == TOOL_NAME and call["status"] == "success" for call in calls
        )
        correct_citation = row is None or (
            "工艺确认清单" in answer and re.search(rf"(?<!\d){row}(?!\d)", answer)
        )
        first_sentence = re.split(r"[。！\n]", answer.strip("* \n"), maxsplit=1)[0]
        if row in {344, 47, 34}:
            correct_citation = correct_citation and "暂不能确认" in first_sentence
        if "GluerPressureTestV99" in question:
            correct_citation = (
                "工艺确认清单" in answer
                and bool(re.search(r"未覆盖|未收录|没有", first_sentence))
                and bool(re.search(r"暂不能|无法|不能判断", first_sentence))
                and not any(call["name"] == "search_source" for call in calls)
            )
        if question.startswith("点胶相关参数整体"):
            # 默认保护是原表 C 列，待确认的记录也可能填“是”。
            incorrect_protection_count = re.search(
                r"默认保护(?:为|是|=|：)?[“‘「\" ]*是[”’」\" ]*(?:的|为|共)?[\s*]*3\s*条",
                answer,
            )
            correct_citation = correct_citation and not incorrect_protection_count
        report["passed"] = bool(
            correct_tool and correct_citation and all(term in answer for term in terms)
        )
        print(f"{'通过' if report['passed'] else '待复核'} | {question}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--settings-data", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output = arguments.output.resolve()
    if not arguments.output.is_relative_to(ROOT / "output") or arguments.output.exists():
        parser.error("验收报告须写入 output 下的新文件")
    verify(arguments)
