from __future__ import annotations

import os
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool

from app.core.config import get_settings
from app.models import McpServer
from app.runtime.errors import ToolRuntimeError


def validate_mcp_endpoint(endpoint: str) -> str:
    allowed = {item.rstrip("/") for item in get_settings().mcp_allowed_endpoints}
    normalized = endpoint.rstrip("/")
    if normalized not in allowed:
        raise ToolRuntimeError(
            "MCP_ENDPOINT_DENIED", "MCP Server endpoint is not in the configured allowlist."
        )
    return endpoint


def auth_headers(secret_ref: str | None) -> dict[str, str]:
    if secret_ref is None:
        return {}
    if not secret_ref.startswith("env:"):
        raise ToolRuntimeError(
            "MCP_SECRET_REF_INVALID", "Only env: secret references are supported locally."
        )
    variable = secret_ref.removeprefix("env:")
    secret = os.getenv(variable)
    if not secret:
        raise ToolRuntimeError(
            "MCP_SECRET_UNAVAILABLE", "The configured MCP authentication secret is unavailable."
        )
    return {"Authorization": f"Bearer {secret}"}


def serialize_tool(tool: Tool) -> dict[str, Any]:
    return {
        "name": tool.name,
        "title": tool.title,
        "description": tool.description or "External MCP Tool",
        "input_schema": tool.input_schema,
        "output_schema": tool.output_schema,
    }


async def _client_for(server: McpServer):
    endpoint = validate_mcp_endpoint(server.endpoint)
    timeout = get_settings().mcp_connect_timeout_seconds
    client = httpx2.AsyncClient(
        headers=auth_headers(server.auth_secret_ref),
        timeout=httpx2.Timeout(timeout),
        follow_redirects=False,
        trust_env=False,
    )
    return client, Client(streamable_http_client(endpoint, http_client=client))


async def discover_mcp_tools(server: McpServer) -> list[dict[str, Any]]:
    http_client, client = await _client_for(server)
    try:
        tools: list[dict[str, Any]] = []
        cursor: str | None = None
        async with http_client, client:
            while True:
                page = await client.list_tools(cursor=cursor)
                tools.extend(serialize_tool(tool) for tool in page.tools)
                cursor = page.next_cursor
                if cursor is None:
                    return tools
    except ToolRuntimeError:
        raise
    except Exception as error:
        raise ToolRuntimeError(
            "MCP_DISCOVERY_FAILED", "Unable to discover Tools from the MCP Server."
        ) from error


async def execute_mcp_tool(
    server: McpServer, remote_tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    http_client, client = await _client_for(server)
    try:
        async with http_client, client:
            result = await client.call_tool(remote_tool_name, arguments)
    except ToolRuntimeError:
        raise
    except Exception as error:
        raise ToolRuntimeError(
            "MCP_SERVER_UNAVAILABLE",
            "The external MCP Server is unavailable.",
            retryable=True,
        ) from error
    content = [block.model_dump(mode="json", by_alias=True) for block in result.content]
    if result.is_error:
        raise ToolRuntimeError("MCP_TOOL_ERROR", "The external MCP Tool returned an error.")
    return {
        "structured_content": result.structured_content,
        "content": content,
        "is_error": False,
    }
