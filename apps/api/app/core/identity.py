from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.security import Principal, Role


def resolve_local_principal(request: Request, session: Session) -> Principal:
    """Resolve a development identity; replace this provider with OIDC in production."""
    external_id = (
        request.headers.get("X-Local-Principal")
        or get_settings().local_principal_external_id
    )
    principal = session.scalar(
        select(Principal)
        .where(Principal.external_id == external_id)
        .options(selectinload(Principal.roles).selectinload(Role.permissions))
    )
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "PRINCIPAL_NOT_FOUND", "message": "Local principal was not found."},
        )
    if principal.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PRINCIPAL_DISABLED", "message": "Principal is not active."},
        )
    return principal
