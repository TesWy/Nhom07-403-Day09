"""
mcp_dispatch.py — Facade chọn Mock hoặc Advanced MCP theo MCP_MODE.

Dùng trong workers/:
    from mcp_dispatch import dispatch_tool, list_tools

Môi trường:
    MCP_MODE=mock      → dùng mcp_server.py (default)
    MCP_MODE=advanced  → dùng mcp_server_advanced.py qua stdio
"""

import os


def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    mode = os.getenv("MCP_MODE", "mock").lower()
    if mode == "advanced":
        from mcp_client_advanced import dispatch_tool_advanced
        return dispatch_tool_advanced(tool_name, tool_input)
    else:
        from mcp_server import dispatch_tool as mock_dispatch
        return mock_dispatch(tool_name, tool_input)


def list_tools() -> list:
    mode = os.getenv("MCP_MODE", "mock").lower()
    if mode == "advanced":
        from mcp_client_advanced import list_tools_advanced
        return list_tools_advanced()
    else:
        from mcp_server import list_tools as mock_list
        return mock_list()