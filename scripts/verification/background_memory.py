"""用当前供应商在临时库完成真实两阶段记忆验证，不发送或修改正式聊天。"""

import asyncio
import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.runtime.model_budget import ProjectModelBudget  # noqa: E402
from app.bootstrap import create_services  # noqa: E402
from app.core.config import Paths, SettingsStore  # noqa: E402
from app.infrastructure.database.registry import Base  # noqa: E402
from app.infrastructure.providers.models import close_models, create_model  # noqa: E402
from app.modules.chat.models import Thread  # noqa: E402
from app.modules.memory.background import BackgroundMemories  # noqa: E402
from app.modules.memory.models import MemoryExtraction  # noqa: E402
from app.modules.memory.selection import MemorySelection  # noqa: E402


async def verify():
    configuration = SettingsStore(Paths()).load()
    with tempfile.TemporaryDirectory(prefix="arks-memory-verification-") as temporary:
        root = Path(temporary)
        source = root / "source"
        source.mkdir()
        services = create_services(Paths(root / "data", source))
        try:
            Base.metadata.create_all(services.database.engine)
            services.settings.save(configuration.model_copy(update={"auto_memory": True}))
            question = (
                "这是测试聊天。请记住我的稳定回答偏好：默认使用中文，先说明结果，再给出依据。"
                "涉及项目事实时保留适用条件，不把猜测写成已验证结果。"
            )
            run = services.repository.create_run(None, question, [])
            services.repository.finish(run["id"], "收到你的要求，后续回答将遵循上述表达偏好。")
            followup = services.repository.create_run(
                run["thread_id"],
                "补充长期偏好：说明尽量简洁，关键数值和事实依据仍要保留。",
                [],
            )
            services.repository.finish(
                followup["id"], "已理解，简洁表达与保留关键事实需要同时满足。"
            )
            with services.database.session.begin() as session:
                session.get(Thread, run["thread_id"]).updated_at = (
                    datetime.now(UTC) - timedelta(hours=7)
                ).isoformat()
            worker = BackgroundMemories(services)
            await worker.run_once()
            with services.database.session() as session:
                job = session.get(MemoryExtraction, run["thread_id"])
                if not job or job.state != "completed":
                    raise RuntimeError(
                        "真实记忆生成未通过：" + (job.error_code if job else "未调度")
                    )
            model = create_model(configuration.model)
            model.callbacks = [
                ProjectModelBudget(
                    services.runtime.model_ledger,
                    configuration.model.context_tokens,
                    output_tokens=configuration.model.output_tokens,
                )
            ]
            try:
                prompt, included = await MemorySelection(
                    services.memories, model, configuration.model, lambda *_: None
                ).prepare("回答偏好")
            finally:
                await close_models([model])
            if not included or "中文" not in prompt or "依据" not in prompt:
                raise RuntimeError("真实生成结果未保留测试偏好")
            before = job.attempts
            await worker.run_once()
            with services.database.session() as session:
                assert session.get(MemoryExtraction, run["thread_id"]).attempts == before
            print(
                json.dumps(
                    {
                        "passed": True,
                        "state": job.state,
                        "memory_files": len(list(services.paths.memories.rglob("*.md"))),
                        "injected": len(included),
                        "repeated_scan_reused": True,
                    }
                )
            )
        finally:
            services.database.close()


if __name__ == "__main__":
    asyncio.run(verify())
