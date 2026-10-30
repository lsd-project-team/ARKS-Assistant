"""本地 MCP 测试服务；不访问用户源码或模型供应商。"""

from mcp.server import MCPServer

server = MCPServer("contract-test")


@server.tool()
def echo(text: str) -> str:
    """Return supplied text to verify tool schema and Unicode handling."""
    return text


if __name__ == "__main__":
    server.run(transport="stdio")
