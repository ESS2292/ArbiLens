from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.health import HealthResponse
from app.services.health import HealthService
from app.services.storage import ObjectStorageService, get_object_storage_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthService().get_status()


@router.get("/ready", response_model=HealthResponse)
async def readiness_check(
    response: Response,
    session: Session = Depends(get_db_session),
    storage_service: ObjectStorageService = Depends(get_object_storage_service),
) -> HealthResponse:
    readiness = HealthService(session=session, storage_service=storage_service).get_readiness()
    if readiness.status != "ok":
        response.status_code = 503
    return readiness
