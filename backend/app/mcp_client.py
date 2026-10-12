"""官方 MCP SDK 的短连接适配；每个连接在创建任务内关闭。"""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

import httpx2
from langchain_core.tools import StructuredTool, ToolException
from mcp import Client, StdioServerParameters
from mcp_types import Tool

from app.config import McpSettings, dump_json
from app.workspace import content_version


def is_connection_error(error: BaseException) -> bool:
    if isinstance(error, BaseExceptionGroup):
        return any(is_connection_error(child) for child in error.exceptions)
    return isinstance(error, (httpx2.TransportError, TimeoutError, ConnectionError))


@asynccontextmanager
async def http_transport(server: McpSettings):
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamable_http_client

    if server.transport == "sse":
        async with sse_client(server.url, headers=server.headers) as streams:
            yield streams[0], streams[1]
        return
    async with httpx2.AsyncClient(headers=server.headers) as http_client:
        async with streamable_http_client(server.url, http_client=http_client) as streams:
            yield streams[0], streams[1]


@asynccontextmanager
async def connect(server: McpSettings):
    if server.transport == "stdio":
        target = StdioServerParameters(
            command=server.command, args=server.args, env=server.env or None
        )
    else:
        if not server.url.startswith(("http://", "https://")):
            raise ValueError("MCP 地址必须使用 HTTP 或 HTTPS")
        if server.headers or server.transport == "sse":
            target = http_transport(server)
        else:
            target = server.url
    async with Client(target, read_timeout_seconds=45) as client:
        yield client


async def _list_remote_tools(server: McpSettings):
    async with connect(server) as client:
        tools = []
        cursor = None
        for _page in range(20):
            result = await client.list_tools(cursor=cursor)
            tools.extend(result.tools)
            cursor = result.next_cursor
            if not cursor:
                return tools
        raise ValueError("MCP 工具分页数量超过限制")


async def list_remote_tools(server: McpSettings):
    for attempt in range(3):
        try:
            return await _list_remote_tools(server)
        except Exception as error:
            if not is_connection_error(error) or attempt == 2:
                raise
            await asyncio.sleep(0.5 * (attempt + 1))


class ToolCatalog:
    """仅缓存工具定义，不缓存工具执行结果；缓存键包含完整连接配置的摘要。"""

    def __init__(self, folder: Path):
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)
        self.tools = {}
        self.lock = asyncio.Lock()

    def clear(self):
        self.tools.clear()

    async def get(self, server: McpSettings):
        key = content_version(server.model_dump_json().encode())
        async with self.lock:
            if key in self.tools:
                return self.tools[key], False
            target = self.folder / f"{key}.json"
            try:
                tools = await list_remote_tools(server)
                temporary = target.with_suffix(".tmp")
                temporary.write_text(
                    dump_json([item.model_dump(mode="json") for item in tools]), encoding="utf-8"
                )
                temporary.replace(target)
                self.tools[key] = tools
                return tools, False
            except Exception:
                if not target.exists():
                    raise
                rows = json.loads(target.read_text(encoding="utf-8"))
                tools = [Tool.model_validate(row) for row in rows]
                self.tools[key] = tools
                return tools, True


def adapt_tool(
    server: McpSettings, remote, *, workspace=None, repo="", emit=None
) -> StructuredTool:
    async def invoke(**arguments):
        if repo and "deepwiki" in (server.name + server.url).lower():
            field = next(
                (
                    name
                    for name in ("repoName", "repo_name")
                    if name in remote.input_schema.get("properties", {})
                ),
                None,
            )
            if field:
                selected = arguments.get(field)
                if selected not in (None, "") and (
                    not isinstance(selected, str) or selected.strip().casefold() != repo.casefold()
                ):
                    raise ToolException(f"当前项目关联的 DeepWiki 仓库是 {repo}，请使用此仓库")
                # 工具实参绑定项目配置，防止模型沿用另一项目的历史仓库。
                arguments[field] = repo
        try:
            async with connect(server) as client:
                result = await client.call_tool(remote.name, arguments)
        except Exception as error:
            # 将连接故障返回给 Agent，使其可以改查源码；不隐式重试有副作用的工具。
            raise ToolException(f"{server.name} 工具连接失败，请重试或核对本地源码") from error
        # 文档内容属于证据，不能借助 MCP 响应改变用户指令或执行权限。
        payload = result.model_dump(mode="json", by_alias=True)
        if workspace is not None and "deepwiki" in (server.name + server.url).lower():
            from app.wiki_provenance import wiki_provenance

            actual_repo = arguments.get("repoName") or arguments.get("repo_name") or repo
            provenance = await asyncio.to_thread(wiki_provenance, workspace, actual_repo, payload)
            if emit:
                emit("wiki_provenance", {**provenance, "server": server.name, "tool": remote.name})
            payload = {"provenance": provenance, "result": payload}
        return dump_json(payload)

    schema = remote.input_schema
    return StructuredTool(
        name=f"mcp_{server.id}_{remote.name}",
        description=f"[{server.name}] {remote.description or remote.name}",
        args_schema=schema,
        coroutine=invoke,
        handle_tool_error=True,
    )


async def probe_mcp(server: McpSettings) -> dict:
    tools = await list_remote_tools(server)
    return {
        "ok": True,
        "name": server.name,
        "tools": [
            {"name": tool.name, "description": tool.description, "schema": tool.input_schema}
            for tool in tools
        ],
    }
