from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies.billing import require_premium_access
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.reports import ReportGenerateResponse, ReportRead
from app.services.reports import ReportService
from app.services.storage import ObjectStorageService, get_object_storage_service

router = APIRouter()


@router.get("/documents/{document_id}", response_model=list[ReportRead])
def list_reports(
    document_id: UUID,
    current_user: User = Depends(require_premium_access),
    session: Session = Depends(get_db_session),
    storage_service: ObjectStorageService = Depends(get_object_storage_service),
) -> list[ReportRead]:
    reports = ReportService(session, storage_service).list_reports(document_id=document_id, current_user=current_user)
    return [ReportRead.model_validate(report) for report in reports]


@router.post("/documents/{document_id}", response_model=ReportGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_report(
    document_id: UUID,
    current_user: User = Depends(require_premium_access),
    session: Session = Depends(get_db_session),
    storage_service: ObjectStorageService = Depends(get_object_storage_service),
) -> ReportGenerateResponse:
    return ReportService(session, storage_service).generate_report(document_id=document_id, current_user=current_user)


@router.get("/{report_id}", response_model=ReportGenerateResponse)
def get_report(
    report_id: UUID,
    current_user: User = Depends(require_premium_access),
    session: Session = Depends(get_db_session),
    storage_service: ObjectStorageService = Depends(get_object_storage_service),
) -> ReportGenerateResponse:
    return ReportService(session, storage_service).get_report_download(report_id=report_id, current_user=current_user)
