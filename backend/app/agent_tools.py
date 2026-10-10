"""小工具只承担一种任务；来源和权限由服务层处理。"""

import asyncio

from langchain_core.tools import tool

from app.config import dump_json
from app.memory import MemoryService
from app.repository import Repository
from app.schemas import MemoryWrite
from app.workspace import Workspace


def source_tools(workspace: Workspace):
    @tool
    async def read_source(path: str, start_line: int = 1, end_line: int = 200) -> str:
        """Read source with explicit 1-based line numbers and SHA256 version for citations."""
        source = await asyncio.to_thread(workspace.read, path)
        lines = source["content"].splitlines()
        start_line = max(1, start_line)
        end_line = min(len(lines), end_line, start_line + 499)
        return dump_json(
            {
                "path": source["path"],
                "version": source["version"],
                "lines": [
                    {"line": line, "text": lines[line - 1]}
                    for line in range(start_line, end_line + 1)
                ],
            }
        )

    @tool
    async def search_source(query: str, glob: str = "*") -> str:
        """Search literal text in trunk source, returning paths and numbered snippets."""
        return dump_json(await asyncio.to_thread(workspace.search, query, glob))

    @tool
    async def find_source_files(query: str) -> str:
        """Find source files whose relative path contains query; ignores generated folders."""
        return dump_json(await asyncio.to_thread(workspace.find_files, query))

    @tool
    async def csharp_symbols(path: str) -> str:
        """List C# syntax declarations and line ranges; does not perform semantic analysis."""
        return dump_json(await asyncio.to_thread(workspace.symbols, path))

    return [read_source, search_source, find_source_files, csharp_symbols]


def conversation_tools(repository: Repository, memories: MemoryService, thread_id: str):
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

        Include source paths for project facts. Never save credentials or guesses.
        """
        try:
            previous = memories.read(scope, name)
            version = previous["version"]
        except FileNotFoundError:
            version = None
        request = MemoryWrite(
            name=name,
            content=content,
            scope=scope,
            version=version,
            source_thread_id=thread_id,
            source_paths=source_paths or [],
        )
        return dump_json(await asyncio.to_thread(memories.save, request))

    return [recall_conversation, read_conversation_message, remember]
