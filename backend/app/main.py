import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import RequestContextFilter, configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
    )

    request_context_filter = RequestContextFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(request_context_filter)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        started_at = perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        return response

    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        return {"message": "ArbiLens API"}

    return app


app = create_app()
