from typing import Any

from sqlalchemy.orm import Session

from app.core.redaction import redact_value
from app.models import AuditEvent, Principal


def append_audit_event(
    session: Session,
    *,
    workspace_id: str,
    principal: Principal | None,
    action: str,
    resource_type: str,
    resource_id: str,
    decision: str,
    trace_id: str,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        workspace_id=workspace_id,
        actor_principal_id=principal.id if principal else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        decision=decision,
        trace_id=trace_id,
        metadata_redacted=redact_value(metadata or {}),
    )
    session.add(event)
    return event
