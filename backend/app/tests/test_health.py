from fastapi.testclient import TestClient
import pytest

from app.services.health import HealthService


def test_health_service_reports_ok() -> None:
    response = HealthService().get_status()
    assert response.status == "ok"
    assert response.service == "arbilens-api"


def test_health_service_readiness_detects_dependency_failure() -> None:
    readiness = HealthService(
        session=None,
        redis_factory=lambda: (_ for _ in ()).throw(RuntimeError("redis unavailable")),
        storage_service=None,
    ).get_readiness()

    assert readiness.status == "degraded"
    assert readiness.checks == {
        "database": "unavailable",
        "redis": "error",
        "object_storage": "unavailable",
    }


def test_readiness_endpoint_reports_ok_with_test_dependencies(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _HealthyRedis:
        def ping(self) -> None:
            return None

    monkeypatch.setattr(HealthService, "_default_redis_factory", lambda self: _HealthyRedis())
    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["object_storage"] == "ok"
