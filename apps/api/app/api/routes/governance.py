from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import append_audit_event
from app.core.config import get_settings
from app.core.identity import resolve_local_principal
from app.core.policy import principal_permissions
from app.db.session import get_db_session, normalize_database_url
from app.models import AuditEvent, Permission, Principal, Role
from app.schemas.governance import (
    AuditEventRead,
    DatasourceStatus,
    PermissionRead,
    PrincipalRead,
    PrincipalReference,
    PrincipalRolesUpdate,
    RolePermissionsUpdate,
    RoleRead,
    RoleReference,
)

router = APIRouter(tags=["governance"])
SessionDependency = Annotated[Session, Depends(get_db_session)]


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def principal_query():
    return select(Principal).options(
        selectinload(Principal.roles).selectinload(Role.permissions),
        selectinload(Principal.scoped_agent),
    )


def role_query():
    return select(Role).options(
        selectinload(Role.permissions), selectinload(Role.principals)
    )


def principal_read(principal: Principal) -> PrincipalRead:
    return PrincipalRead(
        id=principal.id,
        type=principal.type,
        display_name=principal.display_name,
        external_id=principal.external_id,
        status=principal.status,
        agent_id=principal.agent_id,
        agent_name=(
            f"{principal.scoped_agent.namespace}.{principal.scoped_agent.name}"
            if principal.scoped_agent
            else None
        ),
        roles=[
            RoleReference(id=role.id, name=role.name, description=role.description)
            for role in sorted(principal.roles, key=lambda item: item.name)
        ],
        permissions=sorted(principal_permissions(principal)),
    )


def role_read(role: Role) -> RoleRead:
    return RoleRead(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=[
            PermissionRead(id=item.id, key=item.key, description=item.description)
            for item in sorted(role.permissions, key=lambda permission: permission.key)
        ],
        principals=[
            PrincipalReference(
                id=item.id, display_name=item.display_name, external_id=item.external_id
            )
            for item in sorted(role.principals, key=lambda principal: principal.display_name)
        ],
    )


def require_admin(request: Request, session: Session) -> Principal:
    principal = resolve_local_principal(request, session)
    if "platform.admin" not in principal_permissions(principal):
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "PERMISSION_DENIED",
            "platform.admin permission is required for this change.",
        )
    return principal


@router.get("/principals", response_model=list[PrincipalRead])
def list_principals(session: SessionDependency) -> list[PrincipalRead]:
    principals = session.scalars(
        principal_query().order_by(Principal.display_name)
    ).unique().all()
    return [principal_read(principal) for principal in principals]


@router.get("/roles", response_model=list[RoleRead])
def list_roles(session: SessionDependency) -> list[RoleRead]:
    roles = session.scalars(role_query().order_by(Role.name)).unique().all()
    return [role_read(role) for role in roles]


@router.get("/permissions", response_model=list[PermissionRead])
def list_permissions(session: SessionDependency) -> list[PermissionRead]:
    permissions = session.scalars(select(Permission).order_by(Permission.key)).all()
    return [
        PermissionRead(id=item.id, key=item.key, description=item.description)
        for item in permissions
    ]


@router.put("/roles/{role_id}/permissions", response_model=RoleRead)
def update_role_permissions(
    role_id: str,
    payload: RolePermissionsUpdate,
    request: Request,
    session: SessionDependency,
) -> RoleRead:
    actor = require_admin(request, session)
    role = session.scalar(role_query().where(Role.id == role_id))
    if role is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "ROLE_NOT_FOUND", "Role was not found.")
    permissions = session.scalars(
        select(Permission).where(Permission.key.in_(set(payload.permission_keys)))
    ).all()
    found = {item.key for item in permissions}
    missing = sorted(set(payload.permission_keys) - found)
    if missing:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "PERMISSION_NOT_FOUND",
            f"Unknown permissions: {', '.join(missing)}",
        )
    role.permissions = list(permissions)
    append_audit_event(
        session,
        workspace_id=role.workspace_id,
        principal=actor,
        action="policy.role_permissions.update",
        resource_type="role",
        resource_id=role.id,
        decision="allowed",
        trace_id=str(uuid4()),
        metadata={"role": role.name, "permission_keys": sorted(found)},
    )
    session.commit()
    refreshed = session.scalar(role_query().where(Role.id == role_id))
    assert refreshed is not None
    return role_read(refreshed)


@router.put("/principals/{principal_id}/roles", response_model=PrincipalRead)
def update_principal_roles(
    principal_id: str,
    payload: PrincipalRolesUpdate,
    request: Request,
    session: SessionDependency,
) -> PrincipalRead:
    actor = require_admin(request, session)
    principal = session.scalar(principal_query().where(Principal.id == principal_id))
    if principal is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "PRINCIPAL_NOT_FOUND", "Principal was not found."
        )
    roles = session.scalars(select(Role).where(Role.name.in_(set(payload.role_names)))).all()
    found = {item.name for item in roles}
    missing = sorted(set(payload.role_names) - found)
    if missing:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "ROLE_NOT_FOUND",
            f"Unknown roles: {', '.join(missing)}",
        )
    principal.roles = list(roles)
    append_audit_event(
        session,
        workspace_id=principal.workspace_id,
        principal=actor,
        action="policy.principal_roles.update",
        resource_type="principal",
        resource_id=principal.id,
        decision="allowed",
        trace_id=str(uuid4()),
        metadata={"principal": principal.external_id, "roles": sorted(found)},
    )
    session.commit()
    refreshed = session.scalar(principal_query().where(Principal.id == principal_id))
    assert refreshed is not None
    return principal_read(refreshed)


@router.get("/audit-events", response_model=list[AuditEventRead])
def list_audit_events(
    session: SessionDependency,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditEventRead]:
    events = session.scalars(
        select(AuditEvent)
        .options(selectinload(AuditEvent.actor))
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    ).all()
    return [
        AuditEventRead(
            id=event.id,
            actor_principal_id=event.actor_principal_id,
            actor_name=event.actor.display_name if event.actor else None,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            decision=event.decision,
            metadata_redacted=event.metadata_redacted,
            trace_id=event.trace_id,
            created_at=event.created_at,
        )
        for event in events
    ]


@router.get("/sql-datasource/status", response_model=DatasourceStatus)
def sql_datasource_status() -> DatasourceStatus:
    settings = get_settings()
    datasource = settings.sql_tool_database_url_value
    metadata = settings.database_url_value
    separated = bool(
        datasource
        and metadata
        and normalize_database_url(datasource) != normalize_database_url(metadata)
    )
    if not datasource:
        detail = "Not configured. Add a dedicated read-only SQL_TOOL_DATABASE_URL."
    elif not separated:
        detail = "Unsafe: the SQL Tool datasource must not reuse DATABASE_URL."
    else:
        detail = "Configured with a connection separate from platform metadata."
    return DatasourceStatus(
        configured=bool(datasource),
        safely_separated=separated,
        allowed_schemas=settings.sql_tool_allowed_schemas,
        statement_timeout_ms=settings.sql_tool_statement_timeout_ms,
        max_rows=settings.sql_tool_absolute_max_rows,
        detail=detail,
    )
