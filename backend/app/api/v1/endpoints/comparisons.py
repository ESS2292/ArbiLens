from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.billing import require_premium_access
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.comparisons import ComparisonResponse
from app.services.comparisons import ComparisonService

router = APIRouter()


@router.get("/documents", response_model=ComparisonResponse)
def compare_documents(
    left_document_id: UUID = Query(...),
    right_document_id: UUID = Query(...),
    current_user: User = Depends(require_premium_access),
    session: Session = Depends(get_db_session),
) -> ComparisonResponse:
    return ComparisonService(session).compare_documents(
        left_document_id=left_document_id,
        right_document_id=right_document_id,
        current_user=current_user,
    )
