from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentStatus, JobStatus


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    status: DocumentStatus
    latest_version_number: int
    created_at: datetime
    updated_at: datetime
    overall_risk_score: int | None = None


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    document_version_id: UUID
    job_id: UUID
    job_status: JobStatus


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class CitationRead(BaseModel):
    char_start: int
    char_end: int
    text: str
    section_title: str | None = None


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    provider: str
    strategy: str
    citations: list[CitationRead]


class DocumentStatusResponse(BaseModel):
    document_id: UUID
    document_version_id: UUID
    document_status: DocumentStatus
    job_id: UUID
    job_status: JobStatus
    current_stage: str
    error_stage: str | None = None
    error_code: str | None = None
    updated_at: datetime
