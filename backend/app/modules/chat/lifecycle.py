"""停止活动运行后修改会话状态；回收站与永久清理使用不同入口。"""

import re
import shutil

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.core.container import AppServices


class ConversationLifecycle:
    def __init__(self, services: AppServices):
        self.services = services

    async def trash(self, thread_id: str):
        services = self.services
        for identifier in services.repository.active_runs(thread_id):
            await services.runs.cancel(identifier)
        return services.repository.catalog.change(thread_id, "deleted")

    async def purge(self, thread_id: str):
        services = self.services
        row = services.repository.catalog.get(thread_id, include_deleted=True)
        if row["state"] != "deleted":
            raise ValueError("请先将对话移入回收站")
        async with AsyncSqliteSaver.from_conn_string(
            str(services.paths.data / "checkpoints.sqlite3")
        ) as saver:
            sessions = set()
            # 旧版压缩档案使用随机 session 文件名，检查所有检查点才能完整归属。
            for generation in range(row.get("context_generation", 0) + 1):
                checkpoint_id = f"{thread_id}:project:{generation}" if generation else thread_id
                config = {"configurable": {"thread_id": checkpoint_id}}
                async for saved in saver.alist(config):
                    identifier = saved.checkpoint.get("channel_values", {}).get(
                        "_summarization_session_id"
                    )
                    if isinstance(identifier, str) and re.fullmatch(
                        r"session_[a-f0-9]{32}", identifier
                    ):
                        sessions.add(identifier)
                await saver.adelete_thread(checkpoint_id)
        root = services.paths.scratch.resolve()
        for identifier in sessions:
            archive = (root / "conversation_history" / f"{identifier}.md").resolve()
            if archive.is_relative_to(root):
                archive.unlink(missing_ok=True)
        folder = (root / "threads" / thread_id).resolve()
        # 路径来自已验证的会话 ID，仍在递归清理前检查最终绝对路径边界。
        if folder.is_relative_to(root / "threads") and folder != root / "threads":
            if folder.exists():
                shutil.rmtree(folder)
        services.repository.catalog.purge(thread_id)
