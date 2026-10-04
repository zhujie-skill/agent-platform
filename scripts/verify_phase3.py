from __future__ import annotations

import asyncio

import httpx2
from mcp import Client

API = "http://127.0.0.1:8000/api/v1"
DATA_AGENT_ID = "00000000-0000-0000-0000-000000000101"
OPERATIONS_AGENT_ID = "00000000-0000-0000-0000-000000000103"


async def invoke(
    client: httpx2.AsyncClient, tool: str, agent_id: str, arguments: dict
) -> dict:
    namespace, name = tool.split(".", maxsplit=1)
    response = await client.post(
        f"{API}/tools/{namespace}/{name}:invoke",
        headers={"X-Local-Principal": "local-admin"},
        json={
            "arguments": arguments,
            "context": {"agent_id": agent_id, "request_source": "phase3-verifier"},
        },
    )
    response.raise_for_status()
    payload = response.json()
    print(f"{tool}: succeeded, trace={payload['trace_id']}")
    return payload


async def main() -> None:
    async with httpx2.AsyncClient(timeout=20, trust_env=False) as http:
        await invoke(http, "system.echo", DATA_AGENT_ID, {"message": "native works"})
        await invoke(http, "http.health_check", OPERATIONS_AGENT_ID, {})
        await invoke(
            http, "external.market-snapshot", DATA_AGENT_ID, {"symbol": "AAPL"}
        )
        metrics = await http.get(f"{API}/metrics/summary?hours=24")
        metrics.raise_for_status()
        print("metrics:", metrics.json()["tools_by_provider"])

    async with Client("http://127.0.0.1:8100/mcp") as client:
        page = await client.list_tools()
        names = [tool.name for tool in page.tools]
        print("Authorized platform tools:", ", ".join(names))
        if "system.echo" not in names:
            raise RuntimeError("system.echo was not exposed by the platform MCP facade")
        result = await client.call_tool("system.echo", {"message": "hello from MCP"})
        if result.is_error:
            raise RuntimeError("Platform MCP call returned an error")
        print("system.echo result:", result.structured_content)


if __name__ == "__main__":
    asyncio.run(main())
