from __future__ import annotations

import asyncio

import httpx2

API = "http://127.0.0.1:8000/api/v1"
DATA_AGENT_ID = "00000000-0000-0000-0000-000000000101"
HEADERS = {"X-Local-Principal": "local-admin"}


async def checked(response: httpx2.Response) -> dict:
    if response.is_error:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
    return response.json()


async def main() -> None:
    async with httpx2.AsyncClient(timeout=20, trust_env=False) as client:
        servers = await checked(await client.get(f"{API}/mcp-servers"))
        server = next((item for item in servers if item["name"] == "demo-market"), None)
        if server is None:
            server = await checked(
                await client.post(
                    f"{API}/mcp-servers",
                    headers=HEADERS,
                    json={
                        "name": "demo-market",
                        "transport": "streamable_http",
                        "endpoint": "http://127.0.0.1:8101/mcp",
                    },
                )
            )
        server = await checked(
            await client.post(f"{API}/mcp-servers/{server['id']}/discover", headers=HEADERS)
        )
        imported = await checked(
            await client.post(
                f"{API}/mcp-servers/{server['id']}/tools/import",
                headers=HEADERS,
                json={
                    "remote_tool_name": "market_snapshot",
                    "namespace": "external",
                    "name": "market-snapshot",
                    "version": "1.0.0",
                    "owner": "External MCP",
                    "risk_level": "low",
                    "required_permissions": [],
                    "make_default": True,
                },
            )
        )
        await checked(
            await client.put(
                f"{API}/agents/{DATA_AGENT_ID}/tools/{imported['id']}",
                headers=HEADERS,
                json={"version_policy": "default", "enabled": True, "configuration": {}},
            )
        )
    print("Registered, discovered, imported and bound external.market-snapshot.")


if __name__ == "__main__":
    asyncio.run(main())
