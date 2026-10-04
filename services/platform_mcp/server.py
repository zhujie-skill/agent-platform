from __future__ import annotations

import json
import os
from typing import Any

import httpx2
from mcp import types
from mcp.server.lowlevel import Server

API_URL = os.getenv("PLATFORM_API_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
AGENT_ID = os.getenv(
    "PLATFORM_AGENT_ID", "00000000-0000-0000-0000-000000000101"
)
PRINCIPAL = os.getenv("PLATFORM_PRINCIPAL", "local-admin")


def headers() -> dict[str, str]:
    return {"X-Local-Principal": PRINCIPAL}


async def fetch_available_tools() -> list[dict[str, Any]]:
    async with httpx2.AsyncClient(timeout=10, trust_env=False) as client:
        response = await client.get(
            f"{API_URL}/agents/{AGENT_ID}/available-tools", headers=headers()
        )
        response.raise_for_status()
        return response.json()


async def list_tools(
    _context: Any, _params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    definitions = await fetch_available_tools()
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name=definition["name"],
                title=definition["title"],
                description=definition["description"],
                input_schema=definition["input_schema"],
            )
            for definition in definitions
        ]
    )


async def call_tool(
    _context: Any, params: types.CallToolRequestParams
) -> types.CallToolResult:
    async with httpx2.AsyncClient(timeout=30, trust_env=False) as client:
        namespace, separator, name = params.name.partition(".")
        if not separator:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text="Invalid platform Tool name.")],
                is_error=True,
            )
        response = await client.post(
            f"{API_URL}/tools/{namespace}/{name}:invoke",
            headers=headers(),
            json={
                "arguments": params.arguments or {},
                "context": {
                    "agent_id": AGENT_ID,
                    "request_source": "mcp-client",
                },
            },
        )
    payload = response.json()
    if response.is_error:
        detail = payload.get("detail", {}) if isinstance(payload, dict) else {}
        message = detail.get("message", f"Platform returned HTTP {response.status_code}")
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=message)], is_error=True
        )
    data = payload.get("data", {})
    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text", text=json.dumps(data, ensure_ascii=False, default=str)
            )
        ],
        structured_content=data,
        is_error=False,
    )


server = Server(
    "Agent Tool Platform",
    version="0.5.0",
    description="Policy-aware MCP facade for the platform Tool Registry.",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)

app = server.streamable_http_app(
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
    host=os.getenv("PLATFORM_MCP_HOST", "127.0.0.1"),
)
