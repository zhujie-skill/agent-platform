from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import McpServer, ToolVersion
from app.runtime.errors import ToolRuntimeError
from app.runtime.http_executor import execute_http_tool
from app.runtime.mcp_adapter import execute_mcp_tool
from app.runtime.native import execute_native, has_native_handler


def executor_available(session: Session, version: ToolVersion) -> bool:
    if version.executor_type == "native":
        return has_native_handler(str(version.executor_config.get("handler_key", "")))
    if version.executor_type == "http":
        return True
    if version.executor_type == "mcp":
        server_id = str(version.executor_config.get("mcp_server_id", ""))
        server = session.get(McpServer, server_id)
        return server is not None and server.status in {"configured", "healthy"}
    return False


async def execute_tool_version(
    session: Session, version: ToolVersion, arguments: dict[str, Any]
) -> dict[str, Any]:
    if version.executor_type == "native":
        handler_key = str(version.executor_config.get("handler_key", ""))
        if not has_native_handler(handler_key):
            raise ToolRuntimeError(
                "EXECUTOR_UNAVAILABLE", "The native handler is unavailable in this deployment."
            )
        return await execute_native(handler_key, arguments)
    if version.executor_type == "http":
        return await execute_http_tool(version.executor_config, arguments)
    if version.executor_type == "mcp":
        server_id = str(version.executor_config.get("mcp_server_id", ""))
        remote_name = str(version.executor_config.get("remote_tool_name", ""))
        server = session.get(McpServer, server_id)
        if server is None or server.status not in {"configured", "healthy"}:
            raise ToolRuntimeError(
                "MCP_SERVER_UNAVAILABLE", "The configured MCP Server is unavailable."
            )
        return await execute_mcp_tool(server, remote_name, arguments)
    raise ToolRuntimeError("EXECUTOR_UNAVAILABLE", "Tool executor type is unsupported.")
