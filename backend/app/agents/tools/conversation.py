"""按需找回当前聊天原文；记忆由独立后台流程生成。"""

import asyncio

from langchain_core.tools import tool

from app.agents.tools.guards import safe_source_tools
from app.core.config import dump_json
from app.modules.chat.repository import Repository


def conversation_tools(repository: Repository, thread_id: str):
    @tool
    async def recall_conversation(query: str, offset: int = 0, limit: int = 10) -> str:
        """Search original messages, selections and paths. Page with next_offset."""
        return dump_json(
            await asyncio.to_thread(repository.history.search, thread_id, query, offset, limit)
        )

    @tool
    async def read_conversation_message(message_id: str, offset: int = 0) -> str:
        """Read the original message and selection in 12000-character pages."""
        return dump_json(
            await asyncio.to_thread(repository.history.read, thread_id, message_id, offset)
        )

    return safe_source_tools(
        [recall_conversation, read_conversation_message],
        label="对话工具",
    )
