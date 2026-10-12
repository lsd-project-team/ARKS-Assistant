"""真实模型验收使用隔离目录，凭据只在内存中，不写入报告。"""

import asyncio
import json
import sys
from pathlib import Path

from app.config import Paths, SettingsStore
from app.conversation_context import ConversationContext
from app.database import Database
from app.memory import MemoryService
from app.models import Base
from app.repository import Repository
from app.runs import RunManager
from app.runtime import AgentRuntime
from app.workspace import Workspace

ROOT = Path(__file__).resolve().parents[1]


async def main():
    root = ROOT
    focused = "--focused" in sys.argv or "--delivery" in sys.argv
    destination = (
        root
        / "output"
        / (
            "analysis-upgrade-live-delivery"
            if "--delivery" in sys.argv
            else "analysis-upgrade-live-fixed"
            if focused
            else "analysis-upgrade-live"
        )
    )
    paths = Paths(destination / "data", root / "trunk")
    settings = SettingsStore(Paths(root / "data", root / "trunk")).load()
    settings = settings.model_copy(update={"mcp_servers": [], "auto_memory": False})
    settings.analysis.mode = "deep"
    store = SettingsStore(paths)
    store.load = lambda: settings
    database = Database(paths.data / "app.sqlite3")
    Base.metadata.create_all(database.engine)
    workspace = Workspace(paths.workspace)
    repository = Repository(database, workspace.id)
    memory = MemoryService(paths, database, workspace)
    runtime = AgentRuntime(paths, store, workspace, repository, memory)
    manager = RunManager(repository, runtime, store)
    question = (
        "只核查两项项目进度，不扩展其他模块。先规划源码范围，优先批量读取。"
        "1. AKRS.ZX2200/BondSystem/Models/Programs/S2EpoxyMaterialProgram.cs 的 IsReady，"
        "是否有实际校验缺口，结论不能推广为整个项目没有其他校验。"
        "2. AKRS.ZX2200/BondSystem/BondForce/Services/ForceCalibrationService.cs 的标定提示，"
        "属于功能未实现还是标定前置，空表检查前是否存在集合操作。"
        "按明确实现缺口、标定配置前置、尚未确认范围分类，引用当前行号。"
    )
    if focused:
        question = (
            "核查这两段源码的进度分类，先 plan_source_checks 再 read_source_batch，一次读取两段。"
            "范围仅限 AKRS.ZX2200/BondSystem/Models/Programs/S2EpoxyMaterialProgram.cs:51-62，"
            "及 AKRS.ZX2200/BondSystem/BondForce/Services/ForceCalibrationService.cs:35-82。"
            "第一项直接 return true 是否造成该方法的校验缺口；第二项标定提示是否代表软件未实现，"
            "空表检查之前有没有集合读取。只根据这两个方法分类回答，不搜索调用者和其他类，"
            "其他路径明确标为未核实，不需要拓展分析。附当前行号引用。"
        )
    run = repository.create_run(
        None, question, [], {"use_knowledge": False, "use_memory": False, "use_deepwiki": False}
    )
    manager.start(run)
    async for event in manager.stream(run["id"], 0):
        if event["kind"] == "tool_end":
            print(
                json.dumps(
                    {
                        "kind": "tool_end",
                        "name": event["payload"]["name"],
                        "status": event["payload"]["status"],
                    }
                ),
                flush=True,
            )
    saved = repository.run(run["id"])
    context = ConversationContext(runtime).run_sources(run["id"])
    report = {
        "status": saved["status"],
        "stage": saved["stage"],
        "answer": saved["answer"],
        "completion": context["completion"],
        "policy": context["analysis_plan"],
        "tool_names": [item["name"] for item in context["tools"]],
        "usage": context["provider_usage"],
        "validation": context["answer_validation"],
        "review": context["source_review"],
        "pending": context["analysis_progress"]["pending"]
        if context["analysis_progress"]
        else None,
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": saved["status"],
                "stage": saved["stage"],
                "tools": report["tool_names"],
                "completion": context["completion"],
            },
            ensure_ascii=True,
        ),
        flush=True,
    )
    runtime.semantic.close()
    database.close()
    if saved["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
