"""显式 --live 使用合成记录核对连续追问；正式配置只读，不保存正式聊天。"""

import argparse
import asyncio
import gc
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.context.retrieval_context import retrieval_context
from app.agents.runtime.knowledge_selection import KnowledgeRetrieval
from app.bootstrap import create_services
from app.core.config import Paths, SettingsStore
from app.infrastructure.database.registry import Base
from app.infrastructure.providers.models import close_models, create_model
from app.modules.auth.context import request_identity
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.debug_lookup import DebugIssueLookup
from app.modules.memory.selection import MemorySelection
from tests.helpers.memories import MemorySeed, seed_memory


async def verify():
    configuration = SettingsStore(Paths()).load()
    model = create_model(configuration.model)
    results = []
    with tempfile.TemporaryDirectory(prefix="arks-retrieval-context-") as temporary:
        root = Path(temporary)
        source = root / "source"
        source.mkdir()
        services = create_services(Paths(root / "data", source))
        Base.metadata.create_all(services.database.engine)
        identity = request_identity.set(
            {"user": {"id": "synthetic-account", "role": "admin"}}
        )
        events = []

        def emit(kind, row):
            events.append((kind, row))

        try:
            for device, value in (
                ("A V1", "先释放负压，再核对传感器。"),
                ("B V3", "先确认阀门状态，再核对真空表。"),
            ):
                seed_memory(
                    services.memories,
                    MemorySeed(
                        f"设备{device}真空报警",
                        f"设备{device}真空报警的前置要求：{value}",
                    ),
                )
            context = retrieval_context(
                [
                    {"role": "user", "content": "刚才讨论设备A V1的真空报警。"},
                    {"role": "user", "content": "纠正：现在只问设备B V3的真空报警。"},
                ]
            )
            gate = MemorySelection(services.memories, model, configuration.model, emit)
            prompt, rows = await gate.prepare("它有哪些前置要求？", context=context)
            assert "设备B V3" in prompt and "设备A V1" not in prompt, (
                "记忆筛选未正确使用追问及更正"
            )
            results.append(
                {
                    "case": "memory_followup_correction",
                    "passed": True,
                    "selected": rows[0]["memory_ids"],
                }
            )
            prompt, rows = await gate.prepare(
                "换个话题，介绍一下Vue框架，不讨论设备。", context=context
            )
            assert not prompt and not rows, "切换话题后仍选中了设备记忆"
            results.append({"case": "memory_topic_switch", "passed": True})

            issues = DebugIssues(HandoverStore(database=services.database))
            saved = {}
            for device, value in (("A V1", "历史结果777"), ("B V3", "历史结果42")):
                saved[device] = issues.save(
                    DebugWrite(
                        title=f"设备{device}真空报警",
                        payload={
                            "problem": f"设备{device}真空报警，{value}。",
                            "solution": "核对阀门后复测。",
                            "resolution_status": "resolved",
                        },
                    ),
                    {},
                )
            retrieval = KnowledgeRetrieval(
                DebugIssueLookup(services.database, emit, "它当时怎么处理的？"),
                model,
                "它当时怎么处理的？",
                emit,
                16000,
                context=context,
            )
            report = await retrieval.search_report("真空报警")
            assert {row["id"] for row in report["matches"]} == {saved["B V3"]["id"]}, (
                report["selection_status"]
            )
            # 问的是处理办法，不要求筛选器额外选中无关的试验数值；只核对原文内容。
            selected_content = "\n".join(
                str(row["content"]) for row in report["matches"]
            )
            assert (
                "777" not in selected_content and "核对阀门后复测" in selected_content
            )
            results.append(
                {
                    "case": "knowledge_followup_correction",
                    "passed": True,
                    "selected_count": report["matched"],
                }
            )
            print(
                json.dumps(
                    {
                        "passed": len(results),
                        "cases": results,
                        "usage": [
                            row for kind, row in events if kind == "provider_usage"
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        finally:
            request_identity.reset(identity)
            services.runtime.semantic.close()
            services.database.close()
            await close_models([model])
            # sqlite3 的事务上下文不负责关闭连接，及时回收供 Windows 清理隔离目录。
            gc.collect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        parser.error("真实供应商验收必须显式传入 --live")
    asyncio.run(verify())
