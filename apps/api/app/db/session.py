import logging
from collections.abc import Generator
from functools import lru_cache
from time import perf_counter
from typing import TypedDict

from fastapi import HTTPException, status
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseHealth(TypedDict):
    status: str
    configured: bool
    latency_ms: int | None
    detail: str


def normalize_database_url(url: str) -> str:
    """Use SQLAlchemy's psycopg v3 dialect for common provider URLs."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache
def get_engine() -> Engine | None:
    settings = get_settings()
    database_url = settings.database_url_value
    if database_url is None:
        return None

    return create_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
        echo=settings.sql_echo,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session] | None:
    engine = get_engine()
    if engine is None:
        return None
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional request session or a clear degraded-mode error."""
    factory = get_session_factory()
    if factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": "DATABASE_URL is not configured.",
            },
        )

    with factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


def check_database() -> DatabaseHealth:
    engine = get_engine()
    if engine is None:
        return {
            "status": "unconfigured",
            "configured": False,
            "latency_ms": None,
            "detail": "DATABASE_URL is not configured; the API is running in degraded mode.",
        }

    started_at = perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        latency_ms = round((perf_counter() - started_at) * 1000)
        return {
            "status": "ok",
            "configured": True,
            "latency_ms": latency_ms,
            "detail": "Cloud PostgreSQL connection is healthy.",
        }
    except SQLAlchemyError as error:
        logger.warning("Database health check failed with %s", error.__class__.__name__)
        return {
            "status": "error",
            "configured": True,
            "latency_ms": None,
            "detail": "Cloud PostgreSQL is configured but currently unreachable.",
        }

