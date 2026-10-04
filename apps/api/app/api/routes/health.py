from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.core.config import get_settings
from app.db.session import check_database

router = APIRouter(prefix="/health", tags=["health"])


class ComponentHealth(BaseModel):
    status: Literal["ok", "unconfigured", "error"]
    configured: bool | None = None
    latency_ms: int | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    environment: str
    timestamp: datetime
    checks: dict[str, ComponentHealth]


async def build_health_response() -> HealthResponse:
    settings = get_settings()
    database = await run_in_threadpool(check_database)
    database_check = ComponentHealth(**database)

    return HealthResponse(
        status="ok" if database_check.status == "ok" else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
        checks={
            "api": ComponentHealth(status="ok", detail="Control API is accepting requests."),
            "database": database_check,
        },
    )


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return an operator-friendly aggregate status without leaking credentials."""
    return await build_health_response()


@router.get("/live")
async def live() -> dict[str, str]:
    """Liveness does not depend on cloud services."""
    return {"status": "ok"}


@router.get("/ready", response_model=HealthResponse)
async def ready() -> HealthResponse:
    """Readiness requires the configured persistence layer to be reachable."""
    response = await build_health_response()
    if response.status != "ok":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The platform is not ready because cloud persistence is unavailable.",
        )
    return response

