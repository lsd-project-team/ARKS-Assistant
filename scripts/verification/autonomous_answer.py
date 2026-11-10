"""显式真实模型验收；只发送合成问题与源码，正式配置只读入内存。"""

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.runtime.engine import AgentRuntime  # noqa: E402
from app.core.config import Paths, SettingsStore  # noqa: E402
from app.infrastructure.database.registry import Base  # noqa: E402
from app.infrastructure.database.session import Database  # noqa: E402
from app.modules.chat.repository import Repository  # noqa: E402
from app.modules.memory.service import MemoryService  # noqa: E402
from app.modules.source_analysis.workspace import Workspace  # noqa: E402


async def verify(output):
    configuration = (
        SettingsStore(Paths())
        .load()
        .model_copy(
            update={"mcp_servers": [], "auto_memory": False, "deepwiki_repo": ""}, deep=True
        )
    )
    with tempfile.TemporaryDirectory(prefix="arks-autonomous-answer-") as temporary:
        directory = Path(temporary)
        source = directory / "source"
        source.mkdir()
        code = 'class Program {\n static void Main() { System.Console.WriteLine("Ready"); }\n}\n'
        (source / "Program.cs").write_text(code, encoding="utf-8")
        paths = Paths(directory / "data", source)
        settings = SettingsStore(paths)
        # 不把正式密钥复制到临时文件；运行期间只通过内存读取配置。
        settings.load = lambda: configuration.model_copy(deep=True)
        database = Database(paths.data / "app.sqlite3")
        Base.metadata.create_all(database.engine)
        workspace = Workspace(source)
        repository = Repository(database, workspace.id)
        runtime = AgentRuntime(
            paths, settings, workspace, repository, MemoryService(paths, database, workspace)
        )
        reports = []
        questions = [
            "请只用一个自然段说明二分查找的基本思路，不使用标题或列表。",
            "请先搜索 Main 并读取 Program.cs，说明入口方法实际做了什么。"
            "用纯 Markdown 两列表格回答，附带已读取源码的行号引用，不使用卡片。",
        ]
        try:
            for index, question in enumerate(questions):
                run = repository.create_run(
                    None,
                    question,
                    [],
                    {"use_knowledge": False, "use_memory": False, "use_deepwiki": False},
                )
                events = []
                answer = await runtime.execute(
                    run, lambda kind, payload, events=events: events.append((kind, payload))
                )
                repository.finish(run["id"], answer)
                tools = [payload["name"] for kind, payload in events if kind == "tool_start"]
                assert answer and "rich-content" not in answer
                assert not any(
                    kind in {"answer_draft", "answer_presentation"} for kind, _ in events
                )
                if index == 0:
                    assert not tools and "\n\n" not in answer.strip(), answer
                else:
                    validation = next(
                        payload for kind, payload in reversed(events) if kind == "answer_validation"
                    )
                    review = next(
                        payload for kind, payload in reversed(events) if kind == "source_review"
                    )
                    assert validation["passed"] and validation["citations"], validation
                    assert review["verdict"] == "passed", review
                    assert "read_source" in tools or "read_source_context" in tools
                    assert "search_source" in tools or "find_source_files" in tools
                    assert "Ready" in answer and "|" in answer, answer
                assert repository.thread(run["thread_id"])["messages"][-1]["content"] == answer
                reports.append(
                    {"question": question, "answer": answer, "tools": tools, "events": events}
                )
                print(
                    f"场景 {index + 1} 通过：{len(answer)} 字符，{len(tools)} 次工具调用",
                    flush=True,
                )
            assert (source / "Program.cs").read_text(encoding="utf-8") == code
        finally:
            runtime.semantic.close()
            database.close()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="使用已配置供应商并消耗模型额度")
    parser.add_argument("--output", type=Path, default=ROOT / "output/autonomous-answer/live.json")
    arguments = parser.parse_args()
    if not arguments.live:
        parser.error("真实模型验收必须显式指定 --live")
    destination = arguments.output.resolve()
    if not destination.is_relative_to(ROOT / "output"):
        parser.error("验收结果只能写入 output 目录")
    asyncio.run(verify(destination))
