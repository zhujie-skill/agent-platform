import asyncio
from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import append_audit_event
from app.core.identity import resolve_local_principal
from app.core.policy import PolicyDecision, evaluate_tool_policy, principal_can_act_for_agent
from app.core.redaction import redact_arguments, redact_result
from app.db.session import get_db_session
from app.models import Agent, AgentToolBinding, Execution, Principal, Tool, ToolVersion
from app.runtime.errors import ToolRuntimeError
from app.runtime.executor import execute_tool_version, executor_available
from app.schemas.catalog import ExecutionRead, InvokeMeta, InvokeRequest, InvokeResponse

router = APIRouter(tags=["execution"])
SessionDependency = Annotated[Session, Depends(get_db_session)]


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def append_invoke_audit(
    session: Session,
    *,
    principal: Principal,
    tool: Tool,
    trace_id: str,
    decision: str,
    agent: Agent | None,
    execution: Execution | None = None,
    policy: PolicyDecision | None = None,
    error_code: str | None = None,
) -> None:
    append_audit_event(
        session,
        workspace_id=tool.workspace_id,
        principal=principal,
        action="tool.invoke",
        resource_type="tool",
        resource_id=tool.id,
        decision=decision,
        trace_id=trace_id,
        metadata={
            "tool": f"{tool.namespace}.{tool.name}",
            "agent_id": agent.id if agent else None,
            "agent": f"{agent.namespace}.{agent.name}" if agent else None,
            "execution_id": execution.id if execution else None,
            "required_permissions": policy.required_permissions if policy else [],
            "missing_permissions": policy.missing_permissions if policy else [],
            "risk_level": tool.risk_level,
            "error_code": error_code,
        },
    )


def finish_failed_execution(
    session: Session,
    execution: Execution,
    started: float,
    error_code: str,
    message: str,
    *,
    attempts: int,
    execution_status: str = "failed",
) -> None:
    execution.status = execution_status
    execution.error_code = error_code
    execution.error_message_safe = message
    execution.attempts = attempts
    execution.finished_at = datetime.now(UTC)
    execution.duration_ms = round((perf_counter() - started) * 1000)


def runtime_error_status(code: str) -> int:
    if code in {
        "DATASOURCE_UNAVAILABLE",
        "UNSAFE_DATASOURCE_CONFIGURATION",
        "HTTP_TOOL_UNAVAILABLE",
        "MCP_SERVER_UNAVAILABLE",
    }:
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if code in {"SCHEMA_NOT_ALLOWED", "HTTP_TARGET_DENIED", "MCP_ENDPOINT_DENIED"}:
        return status.HTTP_403_FORBIDDEN
    if code == "TABLE_NOT_FOUND":
        return status.HTTP_404_NOT_FOUND
    return status.HTTP_422_UNPROCESSABLE_CONTENT


@router.post("/tools/{namespace}/{name}:invoke", response_model=InvokeResponse)
async def invoke_tool(
    namespace: str,
    name: str,
    payload: InvokeRequest,
    request: Request,
    session: SessionDependency,
) -> InvokeResponse:
    tool = session.scalar(
        select(Tool).where(Tool.namespace == namespace, Tool.name == name)
    )
    if tool is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "TOOL_NOT_FOUND", "Tool was not found.")

    principal = resolve_local_principal(request, session)
    trace_id = str(uuid4())
    if tool.status != "active":
        append_invoke_audit(
            session,
            principal=principal,
            tool=tool,
            trace_id=trace_id,
            decision="denied",
            agent=None,
            error_code="TOOL_DISABLED",
        )
        session.commit()
        raise api_error(status.HTTP_409_CONFLICT, "TOOL_DISABLED", "Tool is not active.")

    agent = session.get(Agent, payload.context.agent_id)
    if agent is None:
        append_invoke_audit(
            session,
            principal=principal,
            tool=tool,
            trace_id=trace_id,
            decision="denied",
            agent=None,
            error_code="AGENT_NOT_FOUND",
        )
        session.commit()
        raise api_error(status.HTTP_404_NOT_FOUND, "AGENT_NOT_FOUND", "Agent was not found.")
    if agent.status != "active":
        append_invoke_audit(
            session,
            principal=principal,
            tool=tool,
            trace_id=trace_id,
            decision="denied",
            agent=agent,
            error_code="AGENT_DISABLED",
        )
        session.commit()
        raise api_error(status.HTTP_409_CONFLICT, "AGENT_DISABLED", "Agent is not active.")
    if not principal_can_act_for_agent(principal, agent.id):
        append_invoke_audit(
            session,
            principal=principal,
            tool=tool,
            trace_id=trace_id,
            decision="denied",
            agent=agent,
            error_code="AGENT_SCOPE_DENIED",
        )
        session.commit()
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "AGENT_SCOPE_DENIED",
            "This service account may only act for its scoped Agent.",
        )

    binding = session.scalar(
        select(AgentToolBinding).where(
            AgentToolBinding.agent_id == agent.id,
            AgentToolBinding.tool_id == tool.id,
        )
    )
    if binding is None or not binding.enabled:
        append_invoke_audit(
            session,
            principal=principal,
            tool=tool,
            trace_id=trace_id,
            decision="denied",
            agent=agent,
            error_code="TOOL_NOT_BOUND",
        )
        session.commit()
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "TOOL_NOT_BOUND",
            "This Tool is not enabled for the selected Agent.",
        )

    requested_version = payload.version
    if binding.version_policy.startswith("exact:"):
        bound_version = binding.version_policy.removeprefix("exact:")
        if requested_version is not None and requested_version != bound_version:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                "TOOL_VERSION_NOT_BOUND",
                "The requested Tool version is outside the Agent binding policy.",
            )
        resolved_version = bound_version
    else:
        resolved_version = requested_version or tool.default_version
    if resolved_version is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "TOOL_VERSION_NOT_CONFIGURED",
            "Tool has no default version and the request did not select one.",
        )
    version = session.scalar(
        select(ToolVersion).where(
            ToolVersion.tool_id == tool.id,
            ToolVersion.version == resolved_version,
        )
    )
    if version is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "TOOL_VERSION_NOT_FOUND",
            "Tool version was not found.",
        )

    handler_key = str(version.executor_config.get("handler_key", ""))
    redaction_key = handler_key or f"{version.executor_type}.{tool.namespace}.{tool.name}"
    policy = evaluate_tool_policy(principal, tool, version)
    started = perf_counter()
    execution = Execution(
        workspace_id=tool.workspace_id,
        agent_id=agent.id,
        agent_tool_binding_id=binding.id,
        tool_id=tool.id,
        tool_version_id=version.id,
        principal_id=principal.id,
        status="running" if policy.allowed else "denied",
        request_source=payload.context.request_source,
        arguments_redacted=redact_arguments(redaction_key, payload.arguments),
        trace_id=trace_id,
        idempotency_key=payload.context.idempotency_key,
        policy_decision=policy.as_dict(),
        attempts=0,
    )
    session.add(execution)
    session.flush()

    if not policy.allowed:
        execution.error_code = "PERMISSION_DENIED"
        execution.error_message_safe = "The current principal lacks required permissions."
        execution.finished_at = datetime.now(UTC)
        execution.duration_ms = round((perf_counter() - started) * 1000)
        append_invoke_audit(
            session,
            principal=principal,
            tool=tool,
            trace_id=trace_id,
            decision="denied",
            agent=agent,
            execution=execution,
            policy=policy,
            error_code="PERMISSION_DENIED",
        )
        session.commit()
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "PERMISSION_DENIED",
            f"Missing permissions: {', '.join(policy.missing_permissions)}",
        )
    session.commit()

    try:
        Draft202012Validator(version.input_schema).validate(payload.arguments)
    except ValidationError as error:
        message = f"Input validation failed: {error.message}"
        finish_failed_execution(
            session, execution, started, "INPUT_VALIDATION_FAILED", message, attempts=0
        )
        append_invoke_audit(
            session,
            principal=principal,
            tool=tool,
            trace_id=trace_id,
            decision="error",
            agent=agent,
            execution=execution,
            policy=policy,
            error_code="INPUT_VALIDATION_FAILED",
        )
        session.commit()
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "INPUT_VALIDATION_FAILED", message
        ) from error

    if not executor_available(session, version):
        message = "The registered Tool executor is unavailable in this deployment."
        finish_failed_execution(
            session, execution, started, "EXECUTOR_UNAVAILABLE", message, attempts=0
        )
        append_invoke_audit(
            session,
            principal=principal,
            tool=tool,
            trace_id=trace_id,
            decision="error",
            agent=agent,
            execution=execution,
            policy=policy,
            error_code="EXECUTOR_UNAVAILABLE",
        )
        session.commit()
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "EXECUTOR_UNAVAILABLE", message)

    retry_safe = bool(version.retry_policy.get("retry_safe", False))
    requested_attempts = int(version.retry_policy.get("max_attempts", 1))
    max_attempts = max(1, min(2, requested_attempts)) if retry_safe else 1
    attempts = 0
    try:
        while True:
            attempts += 1
            try:
                result = await asyncio.wait_for(
                    execute_tool_version(session, version, payload.arguments),
                    timeout=version.timeout_seconds,
                )
                break
            except ToolRuntimeError as error:
                if error.retryable and attempts < max_attempts:
                    continue
                raise
        Draft202012Validator(version.output_schema).validate(result)
    except TimeoutError as error:
        message = "Tool execution exceeded its configured timeout."
        finish_failed_execution(
            session,
            execution,
            started,
            "EXECUTION_TIMEOUT",
            message,
            attempts=attempts,
            execution_status="timed_out",
        )
        error_code = "EXECUTION_TIMEOUT"
        http_status = status.HTTP_504_GATEWAY_TIMEOUT
        caught: Exception = error
    except ToolRuntimeError as error:
        message = error.safe_message
        error_code = error.code
        http_status = runtime_error_status(error.code)
        finish_failed_execution(
            session, execution, started, error.code, message, attempts=attempts
        )
        caught = error
    except ValidationError as error:
        message = "Tool returned a result that does not match its output schema."
        error_code = "OUTPUT_VALIDATION_FAILED"
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        finish_failed_execution(
            session, execution, started, error_code, message, attempts=attempts
        )
        caught = error
    except Exception as error:
        message = "Tool execution failed. Check local server logs for diagnostics."
        error_code = "TOOL_EXECUTION_FAILED"
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        finish_failed_execution(
            session, execution, started, error_code, message, attempts=attempts
        )
        caught = error
    else:
        duration_ms = round((perf_counter() - started) * 1000)
        execution.status = "succeeded"
        execution.result_redacted = redact_result(redaction_key, result)
        execution.finished_at = datetime.now(UTC)
        execution.duration_ms = duration_ms
        execution.attempts = attempts
        append_invoke_audit(
            session,
            principal=principal,
            tool=tool,
            trace_id=trace_id,
            decision="allowed",
            agent=agent,
            execution=execution,
            policy=policy,
        )
        session.commit()
        return InvokeResponse(
            execution_id=execution.id,
            trace_id=execution.trace_id,
            status="succeeded",
            data=result,
            meta=InvokeMeta(
                principal=principal.external_id,
                agent=f"{agent.namespace}.{agent.name}",
                tool=f"{tool.namespace}.{tool.name}",
                version=version.version,
                duration_ms=duration_ms,
                attempts=attempts,
                policy_decision=policy.as_dict(),
            ),
        )

    append_invoke_audit(
        session,
        principal=principal,
        tool=tool,
        trace_id=trace_id,
        decision="error",
        agent=agent,
        execution=execution,
        policy=policy,
        error_code=error_code,
    )
    session.commit()
    raise api_error(http_status, error_code, message) from caught


@router.get("/executions", response_model=list[ExecutionRead])
def list_executions(
    session: SessionDependency,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[ExecutionRead]:
    statement = (
        select(Execution, Agent, Tool, ToolVersion, Principal)
        .join(Agent, Execution.agent_id == Agent.id)
        .join(Tool, Execution.tool_id == Tool.id)
        .join(ToolVersion, Execution.tool_version_id == ToolVersion.id)
        .outerjoin(Principal, Execution.principal_id == Principal.id)
        .order_by(Execution.started_at.desc())
        .limit(limit)
    )
    rows = session.execute(statement).all()
    return [
        ExecutionRead(
            id=execution.id,
            trace_id=execution.trace_id,
            status=execution.status,
            agent_id=agent.id,
            agent_name=agent.display_name,
            principal_id=principal.id if principal else None,
            principal_name=principal.display_name if principal else None,
            tool_id=tool.id,
            tool_name=f"{tool.namespace}.{tool.name}",
            tool_version=version.version,
            request_source=execution.request_source,
            error_code=execution.error_code,
            error_message_safe=execution.error_message_safe,
            started_at=execution.started_at,
            finished_at=execution.finished_at,
            duration_ms=execution.duration_ms,
            attempts=execution.attempts,
            policy_decision=execution.policy_decision,
        )
        for execution, agent, tool, version, principal in rows
    ]
