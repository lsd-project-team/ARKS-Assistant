"""显式真实模型验收：只发送蓝膜案例与合成历史，不读取正式对话或其他资料。"""

import argparse
import asyncio
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.runtime.configuration import bind_configuration  # noqa: E402
from app.agents.runtime.engine import AgentRuntime  # noqa: E402
from app.core.config import AppSettings, Paths, SettingsStore  # noqa: E402
from app.infrastructure.database.registry import Base  # noqa: E402
from app.infrastructure.database.session import Database  # noqa: E402
from app.modules.chat.repository import Repository  # noqa: E402
from app.modules.handover.application.commands import DebugWrite  # noqa: E402
from app.modules.handover.application.debug_issues import DebugIssues  # noqa: E402
from app.modules.handover.infrastructure.persistence.repository import HandoverStore  # noqa: E402
from app.modules.memory.service import MemoryService  # noqa: E402
from app.modules.source_analysis.workspace import Workspace  # noqa: E402

PROBLEM = (
    "芯片规格0.6×0.45mm（微小芯片），调试初期使用025/050顶针，出现蓝膜刺穿、芯片底部残留蓝膜。"
    "尝试降低顶针高度、焊头力、顶针速度均无效。"
)
SOLUTION = "更换075顶针 + 焊头力20~30g + 顶针速度3mm/s + 顶针高度280~300"
RESULT = "连续取放216颗无刺穿，芯片取放稳定，底部残胶改善。"
EXPERIENCE = (
    "微小芯片蓝膜刺穿，小顶针应力集中是主因；换大一号顶针分散受力，配合低速低力才能根治。"
    "只调单项参数效果有限。"
)
ORIGINAL = (
    f"【问题】\n{PROBLEM}\n\n【方案】\n{SOLUTION}\n\n【结果】\n{RESULT}\n\n【经验】\n{EXPERIENCE}"
)
QUESTIONS = {
    "topic": "蓝膜刺穿处理经验",
    "history": "蓝膜刺穿处理经验",
    "advice": "结合蓝膜刺穿处理经验，分析这次调整为什么有效，给出你的建议。",
    "verbatim": "提取蓝膜刺穿处理经验的完整原文，不要改写或分析。",
    "generalize": "蓝膜刺穿是不是用075顶针就能彻底根治，其他尺寸芯片也一样吗？",
}


async def execute_case(config, name):
    with tempfile.TemporaryDirectory(prefix="arks-answer-style-") as directory:
        root = Path(directory)
        workspace_root = root / "source"
        workspace_root.mkdir()
        paths = Paths(root / "data", workspace_root)
        database = Database(paths.data / "app.sqlite3")
        Base.metadata.create_all(database.engine)
        workspace = Workspace(workspace_root)
        repository = Repository(database, workspace.id)
        store = SettingsStore(paths)
        public_config = AppSettings(
            model=config.model.model_copy(update={"api_key": ""}), mcp_servers=[], auto_memory=False
        )
        store.save(public_config)
        memory = MemoryService(paths, database, workspace)
        runtime = AgentRuntime(paths, store, workspace, repository, memory)
        row = DebugIssues(HandoverStore(database=database)).save(
            DebugWrite(
                title="蓝膜刺穿处理经验",
                payload={
                    "problem": ORIGINAL,
                    "solution": SOLUTION,
                    "verification": RESULT,
                    "notes": EXPERIENCE,
                    "resolution_status": "resolved",
                },
            ),
            {"display_name": "隔离验收"},
        )
        options = {"use_memory": False, "use_knowledge": True, "use_deepwiki": False}
        thread = repository.create_thread("隔离的回答表达验收")
        if name == "history":
            previous = repository.create_run(thread["id"], "蓝膜刺穿处理经验", [], options)
            repository.finish(previous["id"], "调试问题库中的记录如下：\n" + ORIGINAL)
        run = repository.create_run(thread["id"], QUESTIONS[name], [], options)
        events = []
        try:
            with bind_configuration(config):
                answer = await asyncio.wait_for(
                    runtime.execute(run, lambda kind, payload: events.append((kind, payload))), 180
                )
            return {
                "case": name,
                "question": QUESTIONS[name],
                "answer": answer,
                "expected_reference": f"debug-issue:{row['id']}/1",
                "usage": [payload for kind, payload in events if kind == "provider_usage"],
                "tools": [payload["name"] for kind, payload in events if kind == "tool_start"],
                "reviews": [
                    payload for kind, payload in events if kind == "knowledge_answer_review"
                ],
                "checks": [payload for kind, payload in events if kind == "knowledge_answer_check"],
                "drafts": [payload["text"] for kind, payload in events if kind == "answer_replace"],
            }
        finally:
            await runtime.project_reading.shutdown()
            await runtime.code_changes.shutdown()
            runtime.semantic.close()
            database.close()


async def main(args):
    selected = SettingsStore(Paths()).load()
    config = AppSettings(model=selected.model, mcp_servers=[], auto_memory=False)
    source = b"".join(
        str(path.relative_to(ROOT)).encode() + path.read_bytes()
        for path in sorted((ROOT / "backend/app").rglob("*.py"))
    )
    result = {
        "model": config.model.model,
        "application_sha256": hashlib.sha256(source).hexdigest(),
        "cases": [],
    }
    output = await asyncio.to_thread(Path(args.output).resolve)
    if not output.is_relative_to(ROOT / "output"):
        raise ValueError("验收结果只能写入项目 output 目录")
    output.parent.mkdir(parents=True, exist_ok=True)
    if len(args.cases) > 5:
        raise ValueError("单次最多执行五个场景")
    for name in args.cases:
        row = await execute_case(config, name)
        result["cases"].append(row)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"model": config.model.model, **row}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--cases", nargs="+", choices=QUESTIONS, default=["topic"])
    parser.add_argument("--output", required=True)
    try:
        asyncio.run(main(parser.parse_args()))
    except Exception as error:
        # API 异常可能含连接配置；终端只报告类型，部分验收结果仍保留在输出文件。
        print(f"验收未完成：{type(error).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
