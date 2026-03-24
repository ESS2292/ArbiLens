from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    document_version_id: UUID | None
    analysis_job_id: UUID | None
    filename: str
    storage_key: str
    report_type: str
    status: str
    file_size_bytes: int | None
    generated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReportGenerateResponse(BaseModel):
    report: ReportRead
    download_url: str
