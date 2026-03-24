from collections.abc import Callable

from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.health import HealthResponse
from app.services.storage import ObjectStorageService


class HealthService:
    def __init__(
        self,
        *,
        session: Session | None = None,
        redis_factory: Callable[[], Redis] | None = None,
        storage_service: ObjectStorageService | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.redis_factory = redis_factory or self._default_redis_factory
        self.storage_service = storage_service

    def get_status(self) -> HealthResponse:
        return HealthResponse(status="ok", service="arbilens-api", version="v1")

    def get_readiness(self) -> HealthResponse:
        checks = {
            "database": self._check_database(),
            "redis": self._check_redis(),
            "object_storage": self._check_object_storage(),
        }
        status = "ok" if all(result == "ok" for result in checks.values()) else "degraded"
        return HealthResponse(status=status, service="arbilens-api", version="v1", checks=checks)

    def _check_database(self) -> str:
        if self.session is None:
            return "unavailable"
        try:
            self.session.execute(text("SELECT 1"))
            return "ok"
        except Exception:
            return "error"

    def _check_redis(self) -> str:
        try:
            self.redis_factory().ping()
            return "ok"
        except Exception:
            return "error"

    def _check_object_storage(self) -> str:
        if self.storage_service is None or not hasattr(self.storage_service, "client"):
            return "unavailable"
        try:
            self.storage_service.client.head_bucket(Bucket=self.settings.s3_bucket)
            return "ok"
        except Exception:
            return "error"

    def _default_redis_factory(self) -> Redis:
        return Redis.from_url(self.settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
