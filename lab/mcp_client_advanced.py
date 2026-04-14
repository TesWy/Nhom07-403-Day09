"""
mcp_client_advanced.py — Async MCP client, wrap thành sync interface.
Spawn mcp_server_advanced.py qua stdio, gọi tool, trả kết quả.
"""

import asyncio
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "mcp_server_advanced.py")


async def _call_tool_async(tool_name: str, arguments: dict) -> Any:
    params = StdioServerParameters(
        command="python",
        args=[SERVER_SCRIPT],
        env=None,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            # FastMCP trả về CallToolResult, lấy content text
            if result.content and len(result.content) > 0:
                import json
                text = result.content[0].text
                try:
                    return json.loads(text)
                except Exception:
                    return {"raw": text}
            return {}


async def _list_tools_async() -> list:
    params = StdioServerParameters(
        command="python",
        args=[SERVER_SCRIPT],
        env=None,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema,
                }
                for t in result.tools
            ]


def dispatch_tool_advanced(tool_name: str, tool_input: dict) -> dict:
    """Sync wrapper — gọi real MCP server qua stdio."""
    try:
        return asyncio.run(_call_tool_async(tool_name, tool_input))
    except Exception as e:
        return {"error": f"Advanced MCP client error: {e}"}


def list_tools_advanced() -> list:
    """Sync wrapper — lấy danh sách tools từ real MCP server."""
    try:
        return asyncio.run(_list_tools_async())
    except Exception as e:
        return [{"error": str(e)}]