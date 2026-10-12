"""显式真实模型验收。使用独立目录，绝不修改用户正式会话和长期记忆。"""

import asyncio
import json
import time

from deepagents.backends import FilesystemBackend
from langchain_core.messages import AIMessage, HumanMessage

from app.config import PROJECT_ROOT, Paths, SettingsStore
from app.context_budget import BudgetedSummarization
from app.models import Base
from app.provider import close_models, create_model
from app.schemas import MemoryWrite
from app.services import create_services
from app.summary_quality import summary_report

PRODUCTION = "AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs"
OPERATE = "AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs"


async def main():
    target = PROJECT_ROOT / "output/quality-evaluation"
    target.mkdir(parents=True, exist_ok=True)
    config = SettingsStore(Paths()).load().model_copy(update={"auto_memory": False})
    services = create_services(Paths(target / "data", PROJECT_ROOT / "trunk"))
    Base.metadata.create_all(services.database.engine)
    services.settings.save(config)
    report_path = target / "report.json"
    report = (
        json.loads(report_path.read_text(encoding="utf-8"))
        if report_path.exists()
        else {
            "model": config.model.model,
            "cases": [],
            "limitations": "自动引用检查验证路径/行号/版本/覆盖；语义结论需要结合报告正文复核",
        }
    )
    services.repository.recover()
    if report["cases"]:
        first_run = report["cases"][0]["events"][0]["run_id"]
        thread = services.repository.thread(services.repository.run(first_run)["thread_id"])
    else:
        thread = services.repository.create_thread("真实模型回答质量验收")

    async def ask(name, question, path=None, first=1, last=1, wiki=False):
        if any(item["name"] == name for item in report["cases"]):
            return
        selection = []
        if path:
            source = services.workspace.read(path)
            selection = [
                {
                    "path": path,
                    "start_line": first,
                    "end_line": last,
                    "content": "\n".join(source["content"].splitlines()[first - 1 : last]),
                    "version": source["version"],
                }
            ]
        run = services.repository.create_run(
            thread["id"],
            question,
            selection,
            source_options={"use_memory": False, "use_deepwiki": wiki, "use_knowledge": True},
        )
        started = time.perf_counter()
        answer = await services.runtime.execute(
            run, lambda kind, payload: services.repository.event(run["id"], kind, payload)
        )
        services.repository.finish(run["id"], answer)
        events = services.repository.events(run["id"])
        row = {
            "name": name,
            "question": question,
            "answer": answer,
            "seconds": round(time.perf_counter() - started, 2),
            "events": [
                event
                for event in events
                if event["kind"]
                in {
                    "source_evidence",
                    "answer_validation",
                    "provider_usage",
                    "knowledge_retrieval",
                    "wiki_provenance",
                    "source_relations",
                }
            ],
        }
        report["cases"].append(row)
        (target / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(name, "completed", row["seconds"], flush=True)

    models = []
    try:
        await ask(
            "入口调用顺序",
            "解释 Program.cs 的 Main 调用顺序及每个调用用途，附当前源码引用。",
            "Akrs.ChangeJson/Program.cs",
            16,
            21,
        )
        await ask(
            "取消与 finally",
            "选中的启动按钮里，配方确认被取消时会继续 Machine.Start 吗？"
            "finally 会执行吗？给出条件和源码引用。",
            PRODUCTION,
            74,
            99,
        )
        await ask(
            "启动前检查",
            "解释 PrepareMachineReadyToStart 的提前返回条件，"
            "特别区分安全门检查与安全门已配置的条件。禁止推测设备实际已经运动。",
            OPERATE,
            198,
            227,
        )
        await ask(
            "多轮条件追问",
            "接着刚才 Machine.Operate.cs 的检查：如果 IsSafeDoorConfigured 为 false，"
            "仅因为门没关会被这一分支拒绝启动吗？简短回答并补读当前源码引用。",
        )
        await ask(
            "Wiki 与本地核对",
            "请实际查询 DeepWiki 仓库 lsd-ff/AKRS.ZX2200 关于 Machine.Start 的生产启动架构，"
            "并读取当前 Machine.Operate.cs 核对。标明 Wiki 索引版本是否可知，不要猜测远端提交。",
            OPERATE,
            261,
            285,
            wiki=True,
        )
        model = create_model(config.model, summary=True)
        models.append(model)
        middleware = BudgetedSummarization(
            model,
            backend=FilesystemBackend(services.paths.scratch),
            limit=16384,
            output=4096,
            emit=lambda *_: None,
            trigger=("tokens", 10000),
            keep=("tokens", 2000),
            trim_tokens_to_summarize=6000,
        )
        history = [
            HumanMessage(
                content="目标：分析启动前检查。约束：只能读取源码，不修改；中文；"
                "不可把 Working 软件状态当成设备实际运动。"
                "安全门只有 IsSafeDoorConfigured=true 且门未关闭才在本分支返回 false。依据 source:"
                + OPERATE
                + "#L223-L227。待办：核对日志分支。未知：DevExpress 依赖尚未解析。"
            ),
            AIMessage(content="已确认：取消配方对话提前返回，finally 恢复 Enabled=true。"),
        ]
        summaries = []
        for round_id in range(2):
            history += [HumanMessage(content=("普通背景资料，需保持原有目标、条件和待办。" * 1200))]
            summary = await middleware._acreate_summary(history)
            summaries.append(
                {"round": round_id + 1, "summary": summary, "structure": summary_report(summary)}
            )
            history = [
                HumanMessage(content=summary),
                HumanMessage(content="最新要求：继续核对日志分支，尚未完成。"),
            ]
        report["repeated_compaction"] = summaries
        services.memories.save(
            MemoryWrite(name="启动规则.md", content="启动生产前必须检查安全门已经关闭。")
        )
        proposed = MemoryWrite(name="新启动规则.md", content="启动生产不必检查安全门是否关闭。")
        report["natural_memory_review"] = await services.memories.semantic_review(proposed, model)
        first = services.runtime.semantic.analyze(OPERATE, 223)
        second = services.runtime.semantic.analyze(OPERATE, 223)
        report["incremental_index"] = {
            "first_ms": first["duration_ms"],
            "second_ms": second["duration_ms"],
            "second_stats": second.get("stats"),
            "completeness": second.get("completeness"),
        }
        for case in report["cases"]:
            run_id = case["events"][0]["run_id"]
            all_events, cursor = [], 0
            while True:
                page = services.repository.events(run_id, cursor)
                all_events.extend(page)
                if len(page) < 500:
                    break
                cursor = page[-1]["sequence"]
            case["events"] = [
                event
                for event in all_events
                if event["kind"]
                in {
                    "source_evidence",
                    "answer_validation",
                    "provider_usage",
                    "knowledge_retrieval",
                    "wiki_provenance",
                    "source_relations",
                    "source_review",
                }
            ]
    finally:
        await close_models(models)
        services.runtime.semantic.close()
        services.database.close()
        (target / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    asyncio.run(main())
