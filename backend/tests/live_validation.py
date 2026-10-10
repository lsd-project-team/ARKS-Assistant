"""手动验收：使用本机已配置供应商；不属于默认 pytest，不自动消耗 API。"""

import asyncio
import tempfile
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import Paths, SettingsStore
from app.database import Database
from app.memory import MemoryService
from app.models import Base
from app.repository import Repository
from app.runtime import AgentRuntime
from app.workspace import Workspace


async def validate_compaction(data_dir: Path, config):
    paths = Paths(data_dir=data_dir)
    settings = SettingsStore(paths)
    config.model.context_tokens = 16384
    config.model.output_tokens = 512
    settings.save(config)
    database = Database(paths.data / "app.sqlite3")
    Base.metadata.create_all(database.engine)
    workspace = Workspace(paths.workspace)
    repository = Repository(database, workspace.id)
    memories = MemoryService(paths, database, workspace)
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("隔离的真实压缩验收")
    history = []
    try:
        for index in range(6):
            content = f"原始问题 {index}。目标代号 TRUNK-MEMORY-CHECK。" + "验收上下文" * 600
            run = repository.create_run(thread["id"], content, [])
            message = repository.message(run["message_id"])
            history.extend(
                [
                    HumanMessage(content=content, id=message["id"]),
                    AIMessage(content="原始回答" * 100),
                ]
            )
            repository.finish(run["id"], "原始回答" * 100)
        config = {"configurable": {"thread_id": thread["id"]}}
        async with AsyncSqliteSaver.from_conn_string(
            str(paths.data / "checkpoints.sqlite3")
        ) as saver:
            graph = await runtime.graph(thread["id"], saver, lambda *_event: None)
            await graph.aupdate_state(config, {"messages": history}, as_node="model")
        new_run = repository.create_run(
            thread["id"],
            "请用 recall_conversation 检索 TRUNK-MEMORY-CHECK，并简短回复代号和压缩验证完成。",
            [],
        )
        events = []
        answer = await runtime.execute(
            new_run, lambda kind, payload: events.append((kind, payload))
        )
        assert any(kind == "compaction" for kind, _ in events), "未实际触发上下文压缩"
        assert any(
            kind == "tool_start" and payload["name"] == "recall_conversation"
            for kind, payload in events
        ), "未实际检索原始历史"
        assert "TRUNK-MEMORY-CHECK" in answer
        archives = list(paths.scratch.rglob("*.md"))
        assert archives and any(
            "原始问题 0" in file.read_text(encoding="utf-8") for file in archives
        )
        assert len(repository.thread(thread["id"])["messages"]) == 13
        print("真实模型压缩、压缩档案和原始历史检索已验证。", flush=True)
    finally:
        database.close()


async def main():
    config = SettingsStore(Paths()).load()
    with tempfile.TemporaryDirectory(prefix="trunk-agent-live-") as temporary:
        await validate_compaction(Path(temporary), config)


if __name__ == "__main__":
    asyncio.run(main())
