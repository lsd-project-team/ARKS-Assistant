"""显式真实模型验收：在临时源码和数据库中检查源码回答、建议及原文保留。"""

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from time import monotonic

import httpx
import httpx2
from anthropic import APIError as AnthropicError
from openai import APIError as OpenAIError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.runtime.engine import AgentRuntime  # noqa: E402
from app.core.config import Paths, SettingsStore  # noqa: E402
from app.infrastructure.database.registry import Base  # noqa: E402
from app.infrastructure.database.session import Database  # noqa: E402
from app.modules.chat.repository import Repository  # noqa: E402
from app.modules.chat.rich_presentation import rich_documents  # noqa: E402
from app.modules.memory.service import MemoryService  # noqa: E402
from app.modules.source_analysis.workspace import Workspace  # noqa: E402

SOURCES = {
    "JobRunner.cs": """using System.Collections.Generic;
public sealed class JobRunner
{
    private readonly StepExecutor executor = new StepExecutor();
    public bool TryRun(IReadOnlyList<int> items, int index, bool ready)
    {
        if (!ready) return false;
        int value = items[index];
        if (items == null || index < 0 || index >= items.Count) return false;
        return executor.Execute(value);
    }
}
""",
    "StepExecutor.cs": """public sealed class StepExecutor
{
    public bool Execute(int value)
    {
        return value >= 0;
    }
}
""",
    "FlowController.cs": """using System.Collections.Generic;
public sealed class FlowController
{
    public readonly List<string> Events = new List<string>();
    public bool Run(bool ready, bool vacuumOk)
    {
        if (!ready) return false;
        StartVacuum();
        if (!vacuumOk)
        {
            RaiseAlarm();
            return false;
        }
        MoveToTarget();
        ReleaseVacuum();
        return true;
    }
    private void StartVacuum() { Events.Add("StartVacuum"); }
    private void RaiseAlarm() { Events.Add("RaiseAlarm"); }
    private void MoveToTarget() { Events.Add("MoveToTarget"); }
    private void ReleaseVacuum() { Events.Add("ReleaseVacuum"); }
}
""",
}
QUESTIONS = [
    ("explain", "JobRunner.cs 的 TryRun 方法主要做什么？"),
    ("flow", "FlowController.cs 的 Run 方法有哪些调用路径？说明顺序与失败分支。"),
    (
        "fix",
        (
            "JobRunner.cs 中，ready=true 时，items 为空或 index 越界为何先抛异常，"
            "而没有返回 false？给出修改建议和关键代码。"
        ),
    ),
    ("verbatim", "用 csharp 代码块原样给出 StepExecutor.cs 的完整源码，不加解释。"),
]


async def verify(destination, selected):
    config = (
        SettingsStore(Paths(ROOT / "data"))
        .load()
        .model_copy(
            update={"auto_memory": False, "mcp_servers": [], "deepwiki_repo": ""},
            deep=True,
        )
    )
    reports = []
    with tempfile.TemporaryDirectory(prefix="arks-source-answer-") as temporary:
        directory = Path(temporary)
        source = directory / "source"
        source.mkdir()
        for name, content in SOURCES.items():
            (source / name).write_text(content, encoding="utf-8")
        paths = Paths(directory / "data", source)
        settings = SettingsStore(paths)
        # 正式配置只读入内存，临时目录不保存密钥，也不复制正式聊天。
        settings.load = lambda: config.model_copy(deep=True)
        database = Database(paths.data / "app.sqlite3")
        Base.metadata.create_all(database.engine)
        workspace = Workspace(source)
        repository = Repository(database, workspace.id)
        runtime = AgentRuntime(
            paths,
            settings,
            workspace,
            repository,
            MemoryService(paths, database, workspace),
        )
        try:
            for name, question in QUESTIONS:
                if selected and name not in selected:
                    continue
                events = []
                started = monotonic()
                try:
                    # 各题独立会话，避免上一题答案影响生成和来源范围。
                    run = repository.create_run(
                        None,
                        question,
                        [],
                        {
                            "use_knowledge": False,
                            "use_memory": False,
                            "use_deepwiki": False,
                        },
                    )
                    answer = await runtime.execute(
                        run, lambda kind, payload, events=events: events.append((kind, payload))
                    )
                    repository.finish(run["id"], answer)
                    validations = [p for k, p in events if k == "answer_validation"]
                    reviews = [p for k, p in events if k == "source_review"]
                    documents = list(rich_documents(answer, include_incomplete=True))
                    checks = {
                        "citations": bool(validations and validations[-1]["passed"]),
                        "source_review": bool(reviews and reviews[-1]["verdict"] == "passed"),
                        "format": all(doc is not None for _, _, doc in documents),
                        "history": repository.thread(run["thread_id"])["messages"][-1]["content"]
                        == answer,
                        "source_unchanged": all(
                            (source / path).read_text(encoding="utf-8") == original
                            for path, original in SOURCES.items()
                        ),
                    }
                    if name == "verbatim":
                        checks["verbatim"] = (
                            "```csharp\n" + SOURCES["StepExecutor.cs"] + "```" in answer
                        )
                    result = {
                        "case": name,
                        "question": question,
                        "answer": answer,
                        "checks": checks,
                        "tools": [p["name"] for k, p in events if k == "tool_start"],
                        "events": events,
                    }
                except (
                    ValueError,
                    RuntimeError,
                    TimeoutError,
                    OSError,
                    httpx.HTTPError,
                    httpx2.HTTPError,
                    AnthropicError,
                    OpenAIError,
                ) as error:
                    # 供应商失败仅记录类型，避免异常原文带出配置或认证信息。
                    result = {
                        "case": name,
                        "question": question,
                        "error_type": type(error).__name__,
                    }
                result["duration_seconds"] = round(monotonic() - started, 2)
                reports.append(result)
                destination.write_text(
                    json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(
                    json.dumps(
                        {
                            "case": name,
                            "checks": result.get("checks", {}),
                            "error": result.get("error_type"),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
        finally:
            runtime.semantic.close()
            database.close()
    if any("error_type" in row or not all(row["checks"].values()) for row in reports):
        raise ValueError("源码回答验收有未通过项，输出已保留")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="使用当前供应商并消耗模型额度")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", nargs="+", choices=[name for name, _ in QUESTIONS])
    args = parser.parse_args()
    destination = args.output.resolve()
    if not args.live:
        parser.error("真实模型验收须显式指定 --live")
    if not destination.is_relative_to(ROOT / "output") or destination.exists():
        parser.error("结果须写入 output 下的新文件，不能覆盖既有结果")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # 先独占结果文件，避免两个并发验收在首题完成前误用同一个输出路径。
    with destination.open("x", encoding="utf-8") as reserved:
        reserved.write("[]")
    asyncio.run(verify(destination, set(args.cases or [])))


if __name__ == "__main__":
    main()
