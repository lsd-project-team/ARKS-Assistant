"""Agent 工具适配器；业务规则由对应服务负责。"""

import asyncio

from langchain_core.tools import tool

from app.agents.tools.guards import safe_source_tools
from app.core.config import dump_json
from app.modules.chat.repository import Repository
from app.modules.memory.capture import remember_fact
from app.modules.memory.service import MemoryService


def conversation_tools(
    repository: Repository,
    memories: MemoryService,
    thread_id: str,
    *,
    use_memory=True,
    review_model=None,
    emit=None,
    evidence=None,
    allow_automatic=True,
    request_text="",
):
    @tool
    async def recall_conversation(query: str, offset: int = 0, limit: int = 10) -> str:
        """Search original messages, selections and paths. Page with next_offset.

        Read a partial match with read_conversation_message to retrieve the full original.
        """
        return dump_json(
            await asyncio.to_thread(repository.history.search, thread_id, query, offset, limit)
        )

    @tool
    async def read_conversation_message(message_id: str, offset: int = 0) -> str:
        """Read the original message and selection in 12000-character pages, using next_offset."""
        return dump_json(
            await asyncio.to_thread(repository.history.read, thread_id, message_id, offset)
        )

    @tool
    async def remember(
        name: str, content: str, scope: str = "project", source_paths: list[str] | None = None
    ) -> str:
        """Save durable preferences or verified facts as a named .md memory.

        Use scope='user' for personal preferences. Use scope='project' for shared project facts.
        Include source paths for project facts. Never save credentials or guesses.
        Duplicate content is rejected; related conflicting fields require user review.
        """
        return dump_json(
            await remember_fact(
                memories,
                thread_id,
                evidence,
                review_model,
                emit,
                name=name,
                content=content,
                scope=scope,
                source_paths=source_paths,
                allow_automatic=allow_automatic,
                request_text=request_text,
            )
        )

    return safe_source_tools(
        [recall_conversation, read_conversation_message, *([remember] if use_memory else [])],
        label="对话工具",
    )
