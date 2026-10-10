import sys
from pathlib import Path

import httpx2
from mcp_types import Tool

from app.config import McpSettings
from app.mcp_client import ToolCatalog, adapt_tool, list_remote_tools


async def test_official_stdio_schema_adapter_and_unicode():
    fixture = Path(__file__).parent / "fixtures/mcp_server.py"
    server = McpSettings(
        id="test",
        name="本地测试",
        transport="stdio",
        command=sys.executable,
        args=[str(fixture)],
        env={"PYTHONUTF8": "1"},
    )
    tools = await list_remote_tools(server)
    assert tools[0].name == "echo"
    result = await adapt_tool(server, tools[0]).ainvoke({"text": "中文工具结果"})
    assert "中文工具结果" in result


async def test_catalog_survives_network_failure(tmp_path, monkeypatch):
    server = McpSettings(id="test", name="Test", url="https://example.com/mcp")
    definition = Tool(
        name="read_docs",
        description="Read documentation",
        inputSchema={"type": "object", "properties": {}},
    )

    async def available(_server):
        return [definition]

    monkeypatch.setattr("app.mcp_client.list_remote_tools", available)
    catalog = ToolCatalog(tmp_path / "catalog")
    assert (await catalog.get(server))[1] is False

    async def unavailable(_server):
        raise httpx2.ConnectError("offline")

    monkeypatch.setattr("app.mcp_client.list_remote_tools", unavailable)
    restored = ToolCatalog(tmp_path / "catalog")
    tools, cached = await restored.get(server)
    assert cached and tools[0].name == "read_docs"
