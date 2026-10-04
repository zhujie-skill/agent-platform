from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PermissionRead(BaseModel):
    id: str
    key: str
    description: str


class RoleReference(BaseModel):
    id: str
    name: str
    description: str


class PrincipalReference(BaseModel):
    id: str
    display_name: str
    external_id: str


class PrincipalRead(BaseModel):
    id: str
    type: str
    display_name: str
    external_id: str
    status: str
    agent_id: str | None
    agent_name: str | None
    roles: list[RoleReference]
    permissions: list[str]


class RoleRead(BaseModel):
    id: str
    name: str
    description: str
    permissions: list[PermissionRead]
    principals: list[PrincipalReference]


class RolePermissionsUpdate(BaseModel):
    permission_keys: list[str] = Field(min_length=0)


class PrincipalRolesUpdate(BaseModel):
    role_names: list[str] = Field(min_length=0)


class AuditEventRead(BaseModel):
    id: str
    actor_principal_id: str | None
    actor_name: str | None
    action: str
    resource_type: str
    resource_id: str
    decision: str
    metadata_redacted: dict[str, Any]
    trace_id: str
    created_at: datetime


class DatasourceStatus(BaseModel):
    configured: bool
    safely_separated: bool
    allowed_schemas: list[str]
    statement_timeout_ms: int
    max_rows: int
    detail: str
