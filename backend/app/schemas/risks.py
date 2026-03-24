from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskScope, RiskSeverity
from app.schemas.references import SourceCitation


class RiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    document_version_id: UUID
    clause_id: UUID | None
    analysis_job_id: UUID | None
    scope: RiskScope
    severity: RiskSeverity
    category: str
    title: str
    summary: str
    score: int = Field(ge=0, le=100)
    rationale: str
    recommendation: str
    confidence: float = Field(ge=0, le=1)
    citations: list[SourceCitation]
    deterministic_rule_code: str | None
    evidence_text: str | None
    created_at: datetime
    updated_at: datetime
