from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import httpx2

from app.core.config import get_settings
from app.runtime.errors import ToolRuntimeError


def normalized_origin(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ToolRuntimeError("HTTP_TARGET_DENIED", "HTTP Tool target is invalid.")
    default_port = 443 if parsed.scheme == "https" else 80
    port = parsed.port or default_port
    suffix = "" if port == default_port else f":{port}"
    return f"{parsed.scheme}://{parsed.hostname.lower()}{suffix}"


def resolve_http_url(config: dict[str, Any]) -> str:
    settings = get_settings()
    setting_name = str(config.get("url_setting", ""))
    if setting_name != "http_health_check_url":
        raise ToolRuntimeError(
            "HTTP_TARGET_DENIED", "HTTP Tool must use an approved URL setting."
        )
    url = settings.http_health_check_url
    allowed = {origin.rstrip("/") for origin in settings.http_tool_allowed_origins}
    if normalized_origin(url) not in allowed:
        raise ToolRuntimeError(
            "HTTP_TARGET_DENIED", "HTTP Tool target origin is not allowlisted."
        )
    return url


async def execute_http_tool(
    config: dict[str, Any], arguments: dict[str, Any]
) -> dict[str, Any]:
    settings = get_settings()
    url = resolve_http_url(config)
    method = str(config.get("method", "GET")).upper()
    if method not in {"GET", "POST"}:
        raise ToolRuntimeError("HTTP_METHOD_DENIED", "HTTP Tool method is not supported.")
    request_kwargs: dict[str, Any] = {}
    if bool(config.get("pass_arguments", False)):
        request_kwargs["params" if method == "GET" else "json"] = arguments
    try:
        async with httpx2.AsyncClient(follow_redirects=False, trust_env=False) as client:
            response = await client.request(method, url, **request_kwargs)
    except (httpx2.ConnectError, httpx2.TimeoutException) as error:
        raise ToolRuntimeError(
            "HTTP_TOOL_UNAVAILABLE",
            "The allowlisted HTTP service is unavailable.",
            retryable=True,
        ) from error
    except httpx2.HTTPError as error:
        raise ToolRuntimeError(
            "HTTP_TOOL_FAILED", "The HTTP Tool request failed safely."
        ) from error

    if len(response.content) > settings.http_tool_max_response_bytes:
        raise ToolRuntimeError(
            "HTTP_RESPONSE_TOO_LARGE", "The HTTP Tool response exceeded the configured limit."
        )
    if response.status_code >= 400:
        raise ToolRuntimeError(
            "HTTP_TOOL_RESPONSE_ERROR",
            f"The HTTP service returned status {response.status_code}.",
            retryable=response.status_code >= 500,
        )
    content_type = response.headers.get("content-type", "application/octet-stream")
    if "json" in content_type.lower():
        body: Any = response.json()
    else:
        body = response.text
    return {
        "status_code": response.status_code,
        "content_type": content_type.split(";", maxsplit=1)[0],
        "body": body,
    }
