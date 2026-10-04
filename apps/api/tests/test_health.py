from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness_is_independent_from_database() -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_unconfigured_database(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.health.check_database",
        lambda: {
            "status": "unconfigured",
            "configured": False,
            "latency_ms": None,
            "detail": "DATABASE_URL is not configured; the API is running in degraded mode.",
        },
    )

    response = client.get("/api/v1/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "degraded"
    assert payload["checks"]["api"]["status"] == "ok"
    assert payload["checks"]["database"]["status"] == "unconfigured"


def test_readiness_requires_database(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.health.check_database",
        lambda: {
            "status": "error",
            "configured": True,
            "latency_ms": None,
            "detail": "Cloud PostgreSQL is configured but currently unreachable.",
        },
    )

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert "not ready" in response.json()["detail"]
