from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.core.errors import AppError
from app.db.session import get_db_session
from app.engine.errors import ProviderError
from app.models.user import User
from app.schemas.clauses import ClauseRead
from app.schemas.documents import (
    AskRequest,
    AskResponse,
    CitationRead,
    DocumentListItem,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from app.schemas.risks import RiskRead
from app.schemas.summary import DocumentDetailResponse, DocumentSummaryResponse
from app.services.documents import DocumentService
from app.services.questions import DocumentQuestionService
from app.services.storage import ObjectStorageService, get_object_storage_service
from app.services.summaries import DocumentSummaryService

router = APIRouter()


@router.get("", response_model=list[DocumentListItem])
def list_documents(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
) -> list[DocumentListItem]:
    service = DocumentService(session=session)
    return service.list_documents_for_organization(current_user.organization_id)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
) -> DocumentStatusResponse:
    service = DocumentService(session=session)
    return service.get_document_status(document_id=document_id, current_user=current_user)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
) -> DocumentDetailResponse:
    return DocumentSummaryService(session).get_document(document_id=document_id, current_user=current_user)


@router.get("/{document_id}/summary", response_model=DocumentSummaryResponse)
def get_document_summary(
    document_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
) -> DocumentSummaryResponse:
    return DocumentSummaryService(session).get_summary(document_id=document_id, current_user=current_user)


@router.get("/{document_id}/clauses", response_model=list[ClauseRead])
def get_document_clauses(
    document_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
) -> list[ClauseRead]:
    clauses = DocumentSummaryService(session).get_clauses(document_id=document_id, current_user=current_user)
    return [ClauseRead.model_validate(clause) for clause in clauses]


@router.get("/{document_id}/risks", response_model=list[RiskRead])
def get_document_risks(
    document_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
) -> list[RiskRead]:
    risks = DocumentSummaryService(session).get_risks(document_id=document_id, current_user=current_user)
    return [RiskRead.model_validate(risk) for risk in risks]


@router.post("/{document_id}/ask", response_model=AskResponse)
def ask_document(
    document_id: UUID,
    payload: AskRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
) -> AskResponse:
    try:
        answer = DocumentQuestionService(session).ask(
            document_id=document_id,
            current_user=current_user,
            question=payload.question,
        )
    except ProviderError as exc:
        raise AppError(str(exc), status_code=503, code="provider_not_configured") from exc
    return AskResponse(
        answer=answer.answer,
        grounded=answer.grounded,
        provider=answer.provider,
        strategy=answer.strategy,
        citations=[
            CitationRead(
                char_start=citation.char_start,
                char_end=citation.char_end,
                text=citation.text,
                section_title=citation.section_title,
            )
            for citation in answer.citations
        ],
    )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    upload: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
    storage_service: ObjectStorageService = Depends(get_object_storage_service),
) -> DocumentUploadResponse:
    service = DocumentService(session=session, storage_service=storage_service)
    return await service.upload_document(upload=upload, current_user=current_user)
