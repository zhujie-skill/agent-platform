from __future__ import annotations

from typing import Any

import httpx

from agent_platform_sdk.errors import AgentPlatformError
from agent_platform_sdk.models import InvocationResult, ToolDefinition


class AgentPlatformClient:
    """Small synchronous API v1 client intended for Agent runtimes."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        principal: str,
        timeout_seconds: float = 30,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-Local-Principal": principal},
            timeout=timeout_seconds,
            transport=transport,
            trust_env=False,
        )

    def __enter__(self) -> AgentPlatformClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def compatibility(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/compatibility")

    def list_available_tools(self, agent_id: str) -> list[ToolDefinition]:
        payload = self._request("GET", f"/api/v1/agents/{agent_id}/available-tools")
        return [ToolDefinition.from_dict(item) for item in payload]

    def invoke(
        self,
        tool_name: str,
        *,
        agent_id: str,
        arguments: dict[str, Any],
        version: str | None = None,
        request_source: str = "python-sdk",
        idempotency_key: str | None = None,
    ) -> InvocationResult:
        namespace, separator, name = tool_name.partition(".")
        if not separator or not namespace or not name:
            raise ValueError("tool_name must use the '<namespace>.<name>' format")
        context: dict[str, Any] = {
            "agent_id": agent_id,
            "request_source": request_source,
        }
        if idempotency_key is not None:
            context["idempotency_key"] = idempotency_key
        body: dict[str, Any] = {"arguments": arguments, "context": context}
        if version is not None:
            body["version"] = version
        payload = self._request(
            "POST", f"/api/v1/tools/{namespace}/{name}:invoke", json=body
        )
        return InvocationResult.from_dict(payload)

    def list_executions(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return self._request("GET", "/api/v1/executions", params={"limit": limit})

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise AgentPlatformError(
                "Unable to reach the Agent Tool Platform.",
                code="PLATFORM_UNAVAILABLE",
                status_code=0,
            ) from error
        if response.is_error:
            payload = response.json() if response.content else {}
            detail = payload.get("detail", {}) if isinstance(payload, dict) else {}
            if isinstance(detail, str):
                message, code = detail, "HTTP_ERROR"
            else:
                message = detail.get("message", f"Platform returned HTTP {response.status_code}")
                code = detail.get("code", "HTTP_ERROR")
            raise AgentPlatformError(message, code=code, status_code=response.status_code)
        return response.json()
