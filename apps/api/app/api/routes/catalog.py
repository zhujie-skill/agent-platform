from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import append_audit_event
from app.core.identity import resolve_local_principal
from app.core.policy import (
    evaluate_tool_policy,
    principal_can_act_for_agent,
    principal_permissions,
)
from app.db.session import get_db_session
from app.models import Agent, AgentToolBinding, Tool, ToolVersion, Workspace
from app.runtime.native import has_native_handler
from app.schemas.catalog import (
    AgentCreate,
    AgentRead,
    AgentReference,
    AvailableToolRead,
    BindingUpdate,
    ToolCreate,
    ToolRead,
    ToolReference,
    ToolUpdate,
    ToolVersionCreate,
    ToolVersionRead,
)

router = APIRouter(tags=["catalog"])
SessionDependency = Annotated[Session, Depends(get_db_session)]


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def get_default_workspace(session: Session) -> Workspace:
    workspace = session.scalar(select(Workspace).where(Workspace.slug == "default"))
    if workspace is None:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "WORKSPACE_NOT_INITIALIZED",
            "Run the latest database migration to create the default workspace.",
        )
    return workspace


def require_admin(request: Request, session: Session):
    principal = resolve_local_principal(request, session)
    if "platform.admin" not in principal_permissions(principal):
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "PERMISSION_DENIED",
            "platform.admin permission is required for this change.",
        )
    return principal


def tool_reference(binding: AgentToolBinding) -> ToolReference:
    tool = binding.tool
    return ToolReference(
        id=tool.id,
        namespace=tool.namespace,
        name=tool.name,
        display_name=tool.display_name,
        provider_type=tool.provider_type,
        status=tool.status,
        version_policy=binding.version_policy,
        binding_enabled=binding.enabled,
    )


def agent_reference(binding: AgentToolBinding) -> AgentReference:
    agent = binding.agent
    return AgentReference(
        id=agent.id,
        namespace=agent.namespace,
        name=agent.name,
        display_name=agent.display_name,
        status=agent.status,
        version_policy=binding.version_policy,
        binding_enabled=binding.enabled,
    )


def agent_read(agent: Agent) -> AgentRead:
    bindings = sorted(
        (binding for binding in agent.tool_bindings if binding.enabled),
        key=lambda item: item.tool.display_name.lower(),
    )
    return AgentRead(
        id=agent.id,
        namespace=agent.namespace,
        name=agent.name,
        display_name=agent.display_name,
        description=agent.description,
        agent_type=agent.agent_type,
        status=agent.status,
        owner=agent.owner,
        created_at=agent.created_at,
        tools=[tool_reference(binding) for binding in bindings],
    )


def tool_read(tool: Tool) -> ToolRead:
    versions = sorted(tool.versions, key=lambda item: item.created_at, reverse=True)
    bindings = sorted(
        (binding for binding in tool.agent_bindings if binding.enabled),
        key=lambda item: item.agent.display_name.lower(),
    )
    return ToolRead(
        id=tool.id,
        namespace=tool.namespace,
        name=tool.name,
        display_name=tool.display_name,
        description=tool.description,
        owner=tool.owner,
        provider_type=tool.provider_type,
        risk_level=tool.risk_level,
        status=tool.status,
        default_version=tool.default_version,
        created_at=tool.created_at,
        versions=[ToolVersionRead.model_validate(version) for version in versions],
        consumer_agents=[agent_reference(binding) for binding in bindings],
    )


def agent_query():
    return select(Agent).options(
        selectinload(Agent.tool_bindings).selectinload(AgentToolBinding.tool)
    )


def tool_query():
    return select(Tool).options(
        selectinload(Tool.versions),
        selectinload(Tool.agent_bindings).selectinload(AgentToolBinding.agent),
    )


def validate_tool_version(version: ToolVersionCreate) -> None:
    try:
        Draft202012Validator.check_schema(version.input_schema)
        Draft202012Validator.check_schema(version.output_schema)
    except SchemaError as error:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "INVALID_JSON_SCHEMA",
            error.message,
        ) from error

    if not has_native_handler(version.handler_key):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "NATIVE_HANDLER_NOT_FOUND",
            f"Native handler '{version.handler_key}' is not registered in this deployment.",
        )


def build_definition_hash(version: ToolVersionCreate) -> str:
    definition = {
        "input_schema": version.input_schema,
        "output_schema": version.output_schema,
        "executor_type": "native",
        "executor_config": {"handler_key": version.handler_key},
        "timeout_seconds": version.timeout_seconds,
        "retry_policy": version.retry_policy,
        "required_permissions": version.required_permissions,
    }
    serialized = json.dumps(definition, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode()).hexdigest()


def create_version(payload: ToolVersionCreate) -> ToolVersion:
    validate_tool_version(payload)
    return ToolVersion(
        version=payload.version,
        input_schema=payload.input_schema,
        output_schema=payload.output_schema,
        executor_type="native",
        executor_config={"handler_key": payload.handler_key},
        timeout_seconds=payload.timeout_seconds,
        retry_policy=payload.retry_policy,
        required_permissions=payload.required_permissions,
        definition_hash=build_definition_hash(payload),
        registration_channel=payload.registration_channel,
    )


@router.get("/agents", response_model=list[AgentRead])
def list_agents(session: SessionDependency) -> list[AgentRead]:
    agents = session.scalars(agent_query().order_by(Agent.display_name)).unique().all()
    return [agent_read(agent) for agent in agents]


@router.post("/agents", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, session: SessionDependency) -> AgentRead:
    workspace = get_default_workspace(session)
    existing = session.scalar(
        select(Agent).where(
            Agent.workspace_id == workspace.id,
            Agent.namespace == payload.namespace,
            Agent.name == payload.name,
        )
    )
    if existing is not None:
        raise api_error(status.HTTP_409_CONFLICT, "AGENT_ALREADY_EXISTS", "Agent already exists.")

    agent = Agent(workspace_id=workspace.id, status="active", **payload.model_dump())
    session.add(agent)
    session.commit()
    agent = session.scalar(agent_query().where(Agent.id == agent.id))
    assert agent is not None
    return agent_read(agent)


@router.get("/agents/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: str, session: SessionDependency) -> AgentRead:
    agent = session.scalar(agent_query().where(Agent.id == agent_id))
    if agent is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "AGENT_NOT_FOUND", "Agent was not found.")
    return agent_read(agent)


@router.get("/agents/{agent_id}/available-tools", response_model=list[AvailableToolRead])
def list_available_tools(
    agent_id: str, request: Request, session: SessionDependency
) -> list[AvailableToolRead]:
    principal = resolve_local_principal(request, session)
    agent = session.scalar(agent_query().where(Agent.id == agent_id))
    if agent is None or agent.status != "active":
        raise api_error(status.HTTP_404_NOT_FOUND, "AGENT_NOT_FOUND", "Agent was not found.")
    if not principal_can_act_for_agent(principal, agent.id):
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "AGENT_SCOPE_DENIED",
            "This service account may only act for its scoped Agent.",
        )
    available: list[AvailableToolRead] = []
    for binding in agent.tool_bindings:
        tool = binding.tool
        if not binding.enabled or tool.status != "active":
            continue
        version_name = (
            binding.version_policy.removeprefix("exact:")
            if binding.version_policy.startswith("exact:")
            else tool.default_version
        )
        version = next((item for item in tool.versions if item.version == version_name), None)
        if version is None or version.deprecated_at is not None:
            continue
        policy = evaluate_tool_policy(principal, tool, version)
        if not policy.allowed:
            continue
        available.append(
            AvailableToolRead(
                id=tool.id,
                name=f"{tool.namespace}.{tool.name}",
                title=tool.display_name,
                description=tool.description,
                input_schema=version.input_schema,
                version=version.version,
                provider_type=tool.provider_type,
                risk_level=tool.risk_level,
            )
        )
    return sorted(available, key=lambda item: item.name)


@router.put("/agents/{agent_id}/tools/{tool_id}", response_model=AgentRead)
def bind_tool(
    agent_id: str,
    tool_id: str,
    payload: BindingUpdate,
    session: SessionDependency,
) -> AgentRead:
    agent = session.get(Agent, agent_id)
    tool = session.get(Tool, tool_id)
    if agent is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "AGENT_NOT_FOUND", "Agent was not found.")
    if tool is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "TOOL_NOT_FOUND", "Tool was not found.")
    if agent.workspace_id != tool.workspace_id:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "WORKSPACE_MISMATCH",
            "Agent and Tool must belong to the same workspace.",
        )

    binding = session.scalar(
        select(AgentToolBinding).where(
            AgentToolBinding.agent_id == agent_id,
            AgentToolBinding.tool_id == tool_id,
        )
    )
    if binding is None:
        binding = AgentToolBinding(agent_id=agent_id, tool_id=tool_id)
        session.add(binding)
    binding.version_policy = payload.version_policy
    binding.enabled = payload.enabled
    binding.configuration = payload.configuration
    session.commit()

    refreshed = session.scalar(agent_query().where(Agent.id == agent_id))
    assert refreshed is not None
    return agent_read(refreshed)


@router.delete("/agents/{agent_id}/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def unbind_tool(
    agent_id: str, tool_id: str, session: SessionDependency
) -> Response:
    binding = session.scalar(
        select(AgentToolBinding).where(
            AgentToolBinding.agent_id == agent_id,
            AgentToolBinding.tool_id == tool_id,
        )
    )
    if binding is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "BINDING_NOT_FOUND", "Binding was not found.")
    # Execution history keeps the original binding id, so unbinding is a soft disable.
    binding.enabled = False
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tools", response_model=list[ToolRead])
def list_tools(session: SessionDependency) -> list[ToolRead]:
    tools = session.scalars(tool_query().order_by(Tool.namespace, Tool.name)).unique().all()
    return [tool_read(tool) for tool in tools]


@router.post("/tools", response_model=ToolRead, status_code=status.HTTP_201_CREATED)
def register_tool(payload: ToolCreate, session: SessionDependency) -> ToolRead:
    workspace = get_default_workspace(session)
    existing = session.scalar(
        select(Tool).where(
            Tool.workspace_id == workspace.id,
            Tool.namespace == payload.namespace,
            Tool.name == payload.name,
        )
    )
    if existing is not None:
        raise api_error(status.HTTP_409_CONFLICT, "TOOL_ALREADY_EXISTS", "Tool already exists.")

    version_payload = payload.version
    tool = Tool(
        workspace_id=workspace.id,
        namespace=payload.namespace,
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
        owner=payload.owner,
        provider_type=payload.provider_type,
        risk_level=payload.risk_level,
        status="active",
        default_version=version_payload.version if version_payload.make_default else None,
    )
    tool.versions.append(create_version(version_payload))
    session.add(tool)
    session.commit()

    refreshed = session.scalar(tool_query().where(Tool.id == tool.id))
    assert refreshed is not None
    return tool_read(refreshed)


@router.get("/tools/{tool_id}", response_model=ToolRead)
def get_tool(tool_id: str, session: SessionDependency) -> ToolRead:
    tool = session.scalar(tool_query().where(Tool.id == tool_id))
    if tool is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "TOOL_NOT_FOUND", "Tool was not found.")
    return tool_read(tool)


@router.patch("/tools/{tool_id}", response_model=ToolRead)
def update_tool(
    tool_id: str,
    payload: ToolUpdate,
    request: Request,
    session: SessionDependency,
) -> ToolRead:
    actor = require_admin(request, session)
    tool = session.scalar(tool_query().where(Tool.id == tool_id))
    if tool is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "TOOL_NOT_FOUND", "Tool was not found.")
    changes: dict[str, object] = {}
    if payload.status is not None:
        tool.status = payload.status
        changes["status"] = payload.status
    if "default_version" in payload.model_fields_set:
        if payload.default_version is None:
            tool.default_version = None
        else:
            version = next(
                (item for item in tool.versions if item.version == payload.default_version), None
            )
            if version is None:
                raise api_error(
                    status.HTTP_404_NOT_FOUND,
                    "TOOL_VERSION_NOT_FOUND",
                    "Tool version was not found.",
                )
            if version.deprecated_at is not None:
                raise api_error(
                    status.HTTP_409_CONFLICT,
                    "TOOL_VERSION_DEPRECATED",
                    "A deprecated version cannot become the default.",
                )
            tool.default_version = payload.default_version
        changes["default_version"] = payload.default_version
    append_audit_event(
        session,
        workspace_id=tool.workspace_id,
        principal=actor,
        action="tool.update",
        resource_type="tool",
        resource_id=tool.id,
        decision="allowed",
        trace_id=str(uuid4()),
        metadata={"tool": f"{tool.namespace}.{tool.name}", "changes": changes},
    )
    session.commit()
    refreshed = session.scalar(tool_query().where(Tool.id == tool.id))
    assert refreshed is not None
    return tool_read(refreshed)


@router.post("/tools/{tool_id}/versions/{version_name}/deprecate", response_model=ToolRead)
def deprecate_tool_version(
    tool_id: str,
    version_name: str,
    request: Request,
    session: SessionDependency,
) -> ToolRead:
    actor = require_admin(request, session)
    tool = session.scalar(tool_query().where(Tool.id == tool_id))
    if tool is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "TOOL_NOT_FOUND", "Tool was not found.")
    version = next((item for item in tool.versions if item.version == version_name), None)
    if version is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "TOOL_VERSION_NOT_FOUND", "Tool version was not found."
        )
    if tool.default_version == version_name:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "DEFAULT_VERSION_CANNOT_BE_DEPRECATED",
            "Select another default version before deprecating this version.",
        )
    if version.deprecated_at is None:
        version.deprecated_at = datetime.now(UTC)
        append_audit_event(
            session,
            workspace_id=tool.workspace_id,
            principal=actor,
            action="tool.version.deprecate",
            resource_type="tool_version",
            resource_id=version.id,
            decision="allowed",
            trace_id=str(uuid4()),
            metadata={"tool": f"{tool.namespace}.{tool.name}", "version": version_name},
        )
        session.commit()
    refreshed = session.scalar(tool_query().where(Tool.id == tool.id))
    assert refreshed is not None
    return tool_read(refreshed)


@router.post("/tools/{tool_id}/versions", response_model=ToolRead, status_code=201)
def register_tool_version(
    tool_id: str,
    payload: ToolVersionCreate,
    session: SessionDependency,
) -> ToolRead:
    tool = session.get(Tool, tool_id)
    if tool is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "TOOL_NOT_FOUND", "Tool was not found.")
    duplicate = session.scalar(
        select(ToolVersion).where(
            ToolVersion.tool_id == tool_id,
            ToolVersion.version == payload.version,
        )
    )
    if duplicate is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "TOOL_VERSION_ALREADY_EXISTS",
            "Published Tool versions are immutable.",
        )

    version = create_version(payload)
    version.tool = tool
    session.add(version)
    if payload.make_default:
        tool.default_version = payload.version
    session.commit()
    refreshed = session.scalar(tool_query().where(Tool.id == tool.id))
    assert refreshed is not None
    return tool_read(refreshed)
