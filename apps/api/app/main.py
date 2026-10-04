from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.catalog import router as catalog_router
from app.api.routes.compatibility import router as compatibility_router
from app.api.routes.execution import router as execution_router
from app.api.routes.governance import router as governance_router
from app.api.routes.health import router as health_router
from app.api.routes.mcp import router as mcp_router
from app.api.routes.metrics import router as metrics_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Keep application startup independent from optional cloud services."""
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Control API and execution-plane foundation for the Agent Tool Platform.",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router, prefix=settings.api_prefix)
    application.include_router(catalog_router, prefix=settings.api_prefix)
    application.include_router(execution_router, prefix=settings.api_prefix)
    application.include_router(governance_router, prefix=settings.api_prefix)
    application.include_router(mcp_router, prefix=settings.api_prefix)
    application.include_router(metrics_router, prefix=settings.api_prefix)
    application.include_router(compatibility_router, prefix=settings.api_prefix)

    @application.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": f"{settings.api_prefix}/health",
        }

    return application


app = create_app()

