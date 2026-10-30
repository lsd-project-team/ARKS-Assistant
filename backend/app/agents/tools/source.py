"""Agent 工具适配器；业务规则由对应服务负责。"""

import asyncio
import json

from langchain_core.tools import tool

from app.agents.tools.guards import safe_source_tools, source_path
from app.core.config import dump_json
from app.modules.source_analysis.evidence import enclosing_excerpt, source_excerpt
from app.modules.source_analysis.location import resolve_source_path
from app.modules.source_analysis.reads import SourceRange, batch_source
from app.modules.source_analysis.workspace import Workspace


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
