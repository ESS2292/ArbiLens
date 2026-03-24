from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ClauseType


class ClauseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_version_id: UUID
    chunk_id: UUID | None
    clause_type: ClauseType
    title: str | None
    text: str
    normalized_text: str | None
    confidence: float
    source_method: str
    page_start: int | None
    page_end: int | None
    start_char: int | None
    end_char: int | None
    created_at: datetime
    updated_at: datetime
