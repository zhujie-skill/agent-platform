from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.catalog import get_default_workspace, tool_query, tool_read
from app.core.audit import append_audit_event
from app.core.identity import resolve_local_principal
from app.core.policy import principal_permissions
from app.db.session import get_db_session
from app.models import McpServer, Permission, Tool, ToolVersion
from app.runtime.errors import ToolRuntimeError
from app.runtime.mcp_adapter import discover_mcp_tools, validate_mcp_endpoint
from app.schemas.catalog import ToolRead
from app.schemas.mcp import (
    DiscoveredMcpTool,
    McpServerCreate,
    McpServerRead,
    McpToolImport,
)

router = APIRouter(tags=["mcp"])
SessionDependency = Annotated[Session, Depends(get_db_session)]

MCP_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["content", "is_error"],
    "properties": {
        "structured_content": {},
        "content": {"type": "array"},
        "is_error": {"type": "boolean"},
    },
}


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def require_admin(request: Request, session: Session):
    principal = resolve_local_principal(request, session)
    if "platform.admin" not in principal_permissions(principal):
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "PERMISSION_DENIED",
            "platform.admin permission is required for MCP management.",
        )
    return principal


def remote_schema_hash(tool: dict[str, Any]) -> str:
    payload = {
        "input_schema": tool["input_schema"],
        "output_schema": tool.get("output_schema"),
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def imported_schema_states(session: Session, server: McpServer) -> dict[str, set[str]]:
    states: dict[str, set[str]] = {}
    versions = session.scalars(select(ToolVersion).where(ToolVersion.executor_type == "mcp"))
    for version in versions:
        config = version.executor_config
        if str(config.get("mcp_server_id")) != server.id:
            continue
        remote_name = str(config.get("remote_tool_name", ""))
        states.setdefault(remote_name, set()).add(str(config.get("remote_schema_hash", "")))
    return states


def server_read(session: Session, server: McpServer) -> McpServerRead:
    imported = imported_schema_states(session, server)
    snapshot: list[DiscoveredMcpTool] = []
    for tool in server.discovery_snapshot:
        hashes = imported.get(str(tool["name"]), set())
        current_hash = remote_schema_hash(tool)
        state = "new" if not hashes else "unchanged" if current_hash in hashes else "changed"
        snapshot.append(DiscoveredMcpTool(**tool, import_state=state))
    return McpServerRead(
        id=server.id,
        name=server.name,
        transport=server.transport,
        endpoint=server.endpoint,
        auth_secret_ref=server.auth_secret_ref,
        status=server.status,
        discovery_snapshot=snapshot,
        last_discovered_at=server.last_discovered_at,
        last_error_safe=server.last_error_safe,
        created_at=server.created_at,
    )


@router.get("/mcp-servers", response_model=list[McpServerRead])
def list_mcp_servers(session: SessionDependency) -> list[McpServerRead]:
    servers = session.scalars(select(McpServer).order_by(McpServer.name)).all()
    return [server_read(session, server) for server in servers]


@router.post("/mcp-servers", response_model=McpServerRead, status_code=201)
def register_mcp_server(
    payload: McpServerCreate, request: Request, session: SessionDependency
) -> McpServerRead:
    actor = require_admin(request, session)
    workspace = get_default_workspace(session)
    endpoint = str(payload.endpoint)
    try:
        validate_mcp_endpoint(endpoint)
    except ToolRuntimeError as error:
        raise api_error(status.HTTP_403_FORBIDDEN, error.code, error.safe_message) from error
    existing = session.scalar(
        select(McpServer).where(
            McpServer.workspace_id == workspace.id, McpServer.name == payload.name
        )
    )
    if existing is not None:
        raise api_error(
            status.HTTP_409_CONFLICT, "MCP_SERVER_ALREADY_EXISTS", "MCP Server already exists."
        )
    server = McpServer(
        workspace_id=workspace.id,
        name=payload.name,
        transport=payload.transport,
        endpoint=endpoint,
        auth_secret_ref=payload.auth_secret_ref,
        status="configured",
        discovery_snapshot=[],
    )
    session.add(server)
    session.flush()
    append_audit_event(
        session,
        workspace_id=workspace.id,
        principal=actor,
        action="mcp.server.register",
        resource_type="mcp_server",
        resource_id=server.id,
        decision="allowed",
        trace_id=str(uuid4()),
        metadata={"name": server.name, "endpoint": server.endpoint, "transport": server.transport},
    )
    session.commit()
    return server_read(session, server)


@router.post("/mcp-servers/{server_id}/discover", response_model=McpServerRead)
async def discover_mcp_server(
    server_id: str, request: Request, session: SessionDependency
) -> McpServerRead:
    actor = require_admin(request, session)
    server = session.get(McpServer, server_id)
    if server is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "MCP_SERVER_NOT_FOUND", "MCP Server was not found."
        )
    try:
        snapshot = await discover_mcp_tools(server)
    except ToolRuntimeError as error:
        server.status = "error"
        server.last_error_safe = error.safe_message
        append_audit_event(
            session,
            workspace_id=server.workspace_id,
            principal=actor,
            action="mcp.server.discover",
            resource_type="mcp_server",
            resource_id=server.id,
            decision="error",
            trace_id=str(uuid4()),
            metadata={"name": server.name, "error_code": error.code},
        )
        session.commit()
        raise api_error(status.HTTP_502_BAD_GATEWAY, error.code, error.safe_message) from error
    server.discovery_snapshot = snapshot
    server.last_discovered_at = datetime.now(UTC)
    server.last_error_safe = None
    server.status = "healthy"
    append_audit_event(
        session,
        workspace_id=server.workspace_id,
        principal=actor,
        action="mcp.server.discover",
        resource_type="mcp_server",
        resource_id=server.id,
        decision="allowed",
        trace_id=str(uuid4()),
        metadata={"name": server.name, "tool_count": len(snapshot)},
    )
    session.commit()
    return server_read(session, server)


@router.post("/mcp-servers/{server_id}/tools/import", response_model=ToolRead, status_code=201)
def import_mcp_tool(
    server_id: str,
    payload: McpToolImport,
    request: Request,
    session: SessionDependency,
) -> ToolRead:
    actor = require_admin(request, session)
    server = session.get(McpServer, server_id)
    if server is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "MCP_SERVER_NOT_FOUND", "MCP Server was not found."
        )
    discovered = next(
        (
            tool
            for tool in server.discovery_snapshot
            if tool["name"] == payload.remote_tool_name
        ),
        None,
    )
    if discovered is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "MCP_TOOL_NOT_DISCOVERED",
            "Run discovery before importing this MCP Tool.",
        )
    known_permissions = set(session.scalars(select(Permission.key)).all())
    missing_permissions = sorted(set(payload.required_permissions) - known_permissions)
    if missing_permissions:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "PERMISSION_NOT_FOUND",
            f"Unknown permissions: {', '.join(missing_permissions)}",
        )
    workspace = get_default_workspace(session)
    tool = session.scalar(
        select(Tool).where(
            Tool.workspace_id == workspace.id,
            Tool.namespace == payload.namespace,
            Tool.name == payload.name,
        )
    )
    if tool is None:
        tool = Tool(
            workspace_id=workspace.id,
            namespace=payload.namespace,
            name=payload.name,
            display_name=discovered.get("title") or payload.remote_tool_name,
            description=discovered.get("description") or "External MCP Tool",
            owner=payload.owner,
            provider_type="mcp",
            risk_level=payload.risk_level,
            status="active",
        )
        session.add(tool)
        session.flush()
    elif tool.provider_type != "mcp":
        raise api_error(
            status.HTTP_409_CONFLICT,
            "TOOL_PROVIDER_CONFLICT",
            "An existing Tool with this identity uses another provider type.",
        )

    executor_config = {
        "mcp_server_id": server.id,
        "remote_tool_name": payload.remote_tool_name,
        "remote_schema_hash": remote_schema_hash(discovered),
        "remote_output_schema": discovered.get("output_schema"),
    }
    definition = {
        "input_schema": discovered["input_schema"],
        "output_schema": MCP_OUTPUT_SCHEMA,
        "executor_type": "mcp",
        "executor_config": executor_config,
        "timeout_seconds": 15,
        "retry_policy": {"max_attempts": 1},
        "required_permissions": payload.required_permissions,
    }
    definition_hash = sha256(
        json.dumps(definition, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    duplicate = session.scalar(
        select(ToolVersion).where(
            ToolVersion.tool_id == tool.id, ToolVersion.version == payload.version
        )
    )
    if duplicate is not None:
        if duplicate.definition_hash != definition_hash:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "TOOL_VERSION_ALREADY_EXISTS",
                "This immutable version differs from the discovered MCP schema; "
                "choose a new version.",
            )
    else:
        tool.versions.append(
            ToolVersion(
                version=payload.version,
                input_schema=discovered["input_schema"],
                output_schema=MCP_OUTPUT_SCHEMA,
                executor_type="mcp",
                executor_config=executor_config,
                timeout_seconds=15,
                retry_policy={"max_attempts": 1},
                required_permissions=payload.required_permissions,
                definition_hash=definition_hash,
                registration_channel="mcp_import",
            )
        )
    if payload.make_default:
        tool.default_version = payload.version
    append_audit_event(
        session,
        workspace_id=workspace.id,
        principal=actor,
        action="mcp.tool.import",
        resource_type="tool",
        resource_id=tool.id,
        decision="allowed",
        trace_id=str(uuid4()),
        metadata={
            "server": server.name,
            "remote_tool": payload.remote_tool_name,
            "tool": f"{tool.namespace}.{tool.name}",
            "version": payload.version,
        },
    )
    session.commit()
    refreshed = session.scalar(tool_query().where(Tool.id == tool.id))
    assert refreshed is not None
    return tool_read(refreshed)
