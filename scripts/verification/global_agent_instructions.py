"""当前供应商的合成指令验证；临时库、空源码，不发送正式聊天或持久化密钥。"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.bootstrap import create_services  # noqa: E402
from app.core.config import Paths, SettingsStore  # noqa: E402
from app.infrastructure.database.registry import Base  # noqa: E402
from app.modules.auth.context import request_identity  # noqa: E402
from app.modules.settings.agent_instructions import (  # noqa: E402
    EMPTY_VERSION,
    AgentInstructionsStore,
)


async def verify():
    configuration = (
        SettingsStore(Paths())
        .load()
        .model_copy(
            update={"auto_memory": False, "mcp_servers": [], "deepwiki_repo": ""}, deep=True
        )
    )
    with tempfile.TemporaryDirectory(prefix="arks-instructions-verification-") as temporary:
        root = Path(temporary)
        source = root / "source"
        source.mkdir()
        services = create_services(Paths(root / "data", source))
        token = request_identity.set({"user": {"id": "synthetic-account", "role": "admin"}})
        try:
            Base.metadata.create_all(services.database.engine)
            # 配置仅在内存中供本次执行读取；隔离目录也不保存供应商密钥。
            services.settings.load = lambda: configuration.model_copy(deep=True)
            AgentInstructionsStore(services.paths.data).save(
                "synthetic-account",
                "默认用中文回答，每个回答首行严格写：全局指令生效。之后一句话回答当前问题。",
                EMPTY_VERSION,
            )
            answers = []
            for question in (
                "1加1等于多少？",
                "这次仅回复阿拉伯数字2，不要标题、解释或其他文字。1加1等于多少？",
            ):
                run = services.repository.create_run(
                    None,
                    question,
                    [],
                    {"use_memory": False, "use_knowledge": False, "use_deepwiki": False},
                )
                services.runs.start(run)
                await asyncio.gather(*services.runs.tasks.values())
                result = services.repository.run(run["id"])
                if result["status"] != "completed":
                    raise RuntimeError("真实指令验证的问答未完成")
                answers.append(
                    services.repository.thread(run["thread_id"])["messages"][-1]["content"]
                )
            assert answers[0].startswith("全局指令生效"), "全局默认指令未生效"
            assert answers[1].strip() == "2", "当前明确要求未优先于全局默认指令"
            print(
                json.dumps({"passed": True, "default_applied": True, "current_request_wins": True})
            )
        finally:
            request_identity.reset(token)
            await services.runs.shutdown()
            services.database.close()


if __name__ == "__main__":
    asyncio.run(verify())
