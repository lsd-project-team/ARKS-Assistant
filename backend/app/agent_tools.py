"""小工具只承担一种任务；来源和权限由服务层处理。"""

import asyncio
import json

from langchain_core.tools import ToolException, tool

from app.config import dump_json
from app.memory import MemoryService
from app.repository import Repository
from app.schemas import MemoryWrite
from app.source_evidence import enclosing_excerpt, source_excerpt
from app.source_location import resolve_source_path
from app.source_reads import SourceRange, batch_source
from app.workspace import Workspace


def source_path(path):
    return path.removeprefix("/workspace/")


def safe_source_tools(items, label="源码工具"):
    def guarded(coroutine):
        async def invoke(**arguments):
            try:
                return await coroutine(**arguments)
            except (ValueError, OSError) as error:
                raise ToolException(
                    f"{label}未完成：{error}。请核对参数后重试，失败结果不能作为证据。"
                ) from error

        return invoke

    for item in items:
        item.coroutine = guarded(item.coroutine)
        item.handle_tool_error = True
    return items


def source_tools(workspace: Workspace, evidence=None, progress=None):
    @tool
    async def read_source_batch(ranges: list[SourceRange]) -> str:
        """Read 1–12 source ranges in one call. Adjacent ranges are merged.

        Prefer this for project-wide reviews. Only reads are evidence; errors/remaining
        are still unverified. Each range <=500 lines; total <=1200 lines/12000 tokens.
        """
        return json.dumps(
            await asyncio.to_thread(batch_source, workspace, ranges, evidence),
            ensure_ascii=False,
            indent=2,
        )

    @tool
    async def plan_source_checks(checks: list[SourceRange]) -> str:
        """Plan source checks before a project audit. Track pending paths/ranges and reasons.

        Read coverage is automatic and does not prove a conclusion or project delivery.
        """
        if not progress:
            return dump_json({"recorded": False, "reason": "本运行没有核查记录"})
        progress.plan([row.model_dump() for row in checks])
        return dump_json(progress.snapshot())

    @tool
    async def read_source(path: str, start_line: int = 1, end_line: int = 200) -> str:
        """Read source with explicit 1-based line numbers and SHA256 version for citations."""
        excerpt = await asyncio.to_thread(
            source_excerpt, workspace, resolve_source_path(workspace, path), start_line, end_line
        )
        if evidence:
            evidence.record(excerpt)
        return dump_json(excerpt)

    @tool
    async def read_source_context(path: str, line: int, max_lines: int = 160) -> str:
        """Read the enclosing C# method/property and explicit numbered source near a line.

        complete_symbol=false means only part was read; request the rest if needed.
        """
        excerpt = await asyncio.to_thread(
            enclosing_excerpt,
            workspace,
            resolve_source_path(workspace, path),
            line,
            min(500, max(20, max_lines)),
        )
        if evidence:
            evidence.record(excerpt, "read_source_context")
        return dump_json(excerpt)

    @tool
    async def search_source(query: str, glob: str = "*") -> str:
        """Search literal text across this project's source roots with numbered snippets."""
        return dump_json(await asyncio.to_thread(workspace.search, query, glob))

    @tool
    async def find_source_files(query: str) -> str:
        """Find source files whose relative path contains query; ignores generated folders."""
        return dump_json(await asyncio.to_thread(workspace.find_files, query))

    @tool
    async def csharp_symbols(path: str) -> str:
        """List C# syntax declarations and line ranges; does not perform semantic analysis."""
        return dump_json(await asyncio.to_thread(workspace.symbols, source_path(path)))

    return safe_source_tools(
        [
            read_source,
            read_source_context,
            read_source_batch,
            plan_source_checks,
            search_source,
            find_source_files,
            csharp_symbols,
        ]
    )


def conversation_tools(
    repository: Repository,
    memories: MemoryService,
    thread_id: str,
    *,
    use_memory=True,
    review_model=None,
    emit=None,
    evidence=None,
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

        Include source paths for project facts. Never save credentials or guesses.
        Duplicate content is rejected; related conflicting fields require user review.
        """
        source_paths = [source_path(path) for path in source_paths or []]
        try:
            previous = memories.read(scope, name)
            version = previous["version"]
            if previous.get("lifecycle") in {"invalid", "needs_review"}:
                return dump_json(
                    {
                        "saved": False,
                        "requires_review": True,
                        "reason": "已有记忆处于失效或待复核状态，请到记忆管理核对后更新",
                    }
                )
        except FileNotFoundError:
            version = None
        request = MemoryWrite(
            name=name,
            content=content,
            scope=scope,
            version=version,
            source_thread_id=thread_id,
            source_paths=source_paths or [],
            record_version=previous.get("record_version") if version else None,
            lifecycle="valid"
            if scope == "user"
            or (
                evidence
                and source_paths
                and all(
                    any(
                        row["path"] == path
                        and row["version"] == memories.workspace.read(path)["version"]
                        for row in evidence.reads
                    )
                    for path in source_paths
                )
            )
            else "needs_review",
        )
        matches = await memories.semantic_review(request, review_model, emit)
        if any(row["kind"] == "conflict" for row in matches):
            return dump_json(
                {
                    "saved": False,
                    "requires_review": True,
                    "matches": matches,
                    "reason": "存在潜在矛盾，请用户到记忆管理核对；不可自行确认",
                }
            )
        return dump_json(await asyncio.to_thread(memories.save, request))

    return safe_source_tools(
        [recall_conversation, read_conversation_message, *([remember] if use_memory else [])],
        label="对话工具",
    )
