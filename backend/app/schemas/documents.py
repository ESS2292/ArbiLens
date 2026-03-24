from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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
