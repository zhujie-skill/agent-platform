from __future__ import annotations

import asyncio
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.runtime.errors import ToolRuntimeError
from app.runtime.http_executor import execute_http_tool, resolve_http_url
from tests.conftest import DATA_AGENT_ID, ECHO_TOOL_ID


def test_http_executor_only_uses_allowlisted_configured_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "http_health_check_url", "http://127.0.0.1:8000/health")
    monkeypatch.setattr(settings, "http_tool_allowed_origins", ["http://127.0.0.1:8000"])
    assert resolve_http_url({"url_setting": "http_health_check_url"}).endswith("/health")
    with pytest.raises(ToolRuntimeError):
        resolve_http_url({"url_setting": "arguments.url"})

    transport = httpx2.MockTransport(
        lambda _request: httpx2.Response(
            200, json={"status": "ok"}, headers={"content-type": "application/json"}
        )
    )
    real_client = httpx2.AsyncClient
    monkeypatch.setattr(
        "app.runtime.http_executor.httpx2.AsyncClient",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )
    result = asyncio.run(
        execute_http_tool(
            {"url_setting": "http_health_check_url", "method": "GET"}, {}
        )
    )
    assert result["body"] == {"status": "ok"}


def test_mcp_discovery_import_binding_and_unified_execution(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_discovery(_server: Any) -> list[dict[str, Any]]:
        return [
            {
                "name": "market_snapshot",
                "title": "Market Snapshot",
                "description": "Demo quote",
                "input_schema": {
                    "type": "object",
                    "required": ["symbol"],
                    "properties": {"symbol": {"type": "string"}},
                },
                "output_schema": {"type": "object"},
            }
        ]

    async def fake_execution(
        _server: Any, remote_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        assert remote_name == "market_snapshot"
        return {
            "structured_content": {"symbol": arguments["symbol"], "price": 227.16},
            "content": [],
            "is_error": False,
        }

    monkeypatch.setattr("app.api.routes.mcp.discover_mcp_tools", fake_discovery)
    monkeypatch.setattr("app.runtime.executor.execute_mcp_tool", fake_execution)

    registered = api_client.post(
        "/api/v1/mcp-servers",
        json={
            "name": "test-market",
            "transport": "streamable_http",
            "endpoint": "http://127.0.0.1:8101/mcp",
        },
    )
    assert registered.status_code == 201
    server_id = registered.json()["id"]
    discovered = api_client.post(f"/api/v1/mcp-servers/{server_id}/discover")
    assert discovered.status_code == 200
    assert discovered.json()["discovery_snapshot"][0]["import_state"] == "new"

    imported = api_client.post(
        f"/api/v1/mcp-servers/{server_id}/tools/import",
        json={
            "remote_tool_name": "market_snapshot",
            "namespace": "external",
            "name": "market-snapshot",
            "version": "1.0.0",
            "owner": "Test",
            "risk_level": "low",
            "required_permissions": [],
            "make_default": True,
        },
    )
    assert imported.status_code == 201
    tool_id = imported.json()["id"]
    bound = api_client.put(
        f"/api/v1/agents/{DATA_AGENT_ID}/tools/{tool_id}",
        json={"version_policy": "default", "enabled": True},
    )
    assert bound.status_code == 200

    available = api_client.get(f"/api/v1/agents/{DATA_AGENT_ID}/available-tools")
    assert "external.market-snapshot" in {item["name"] for item in available.json()}
    invoked = api_client.post(
        "/api/v1/tools/external/market-snapshot:invoke",
        json={
            "arguments": {"symbol": "AAPL"},
            "context": {"agent_id": DATA_AGENT_ID, "request_source": "test"},
        },
    )
    assert invoked.status_code == 200
    assert invoked.json()["data"]["structured_content"]["price"] == 227.16


def test_version_deprecation_and_metrics(api_client: TestClient) -> None:
    created = api_client.post(
        f"/api/v1/tools/{ECHO_TOOL_ID}/versions",
        json={
            "version": "1.1.0",
            "input_schema": {
                "type": "object",
                "required": ["message"],
                "properties": {"message": {"type": "string"}},
            },
            "output_schema": {"type": "object"},
            "handler_key": "system.echo",
            "make_default": True,
        },
    )
    assert created.status_code == 201
    deprecated = api_client.post(
        f"/api/v1/tools/{ECHO_TOOL_ID}/versions/1.0.0/deprecate"
    )
    assert deprecated.status_code == 200
    rejected = api_client.patch(
        f"/api/v1/tools/{ECHO_TOOL_ID}", json={"default_version": "1.0.0"}
    )
    assert rejected.status_code == 409

    metrics = api_client.get("/api/v1/metrics/summary?hours=24")
    assert metrics.status_code == 200
    assert metrics.json()["total_agents"] == 2
    assert metrics.json()["tools_by_provider"] == {"native": 1}
