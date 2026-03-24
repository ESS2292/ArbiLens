from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ClauseType, DocumentStatus, JobStatus, RiskSeverity
from app.schemas.references import SourceCitation


class SummaryIssue(BaseModel):
    risk_id: UUID
    category: str
    title: str
    severity: RiskSeverity
    score: int = Field(ge=0, le=100)
    rationale: str
    recommendation: str
    clause_id: UUID | None = None
    citations: list[SourceCitation]

    @model_validator(mode="after")
    def validate_citations(self):
        if not self.citations:
            raise ValueError("summary issues must include at least one source citation")
        return self


class MissingProtectionSummary(BaseModel):
    category: str
    title: str
    risk_id: UUID
    recommendation: str


class NegotiationPrioritySummary(BaseModel):
    priority_rank: int = Field(ge=1)
    risk_id: UUID
    title: str
    category: str
    recommendation: str
    severity: RiskSeverity


class ClauseCoverageItem(BaseModel):
    clause_type: ClauseType
    detected: bool
    clause_count: int = Field(ge=0)
    clause_ids: list[UUID]

    @model_validator(mode="after")
    def validate_detected_and_count(self):
        if self.detected and self.clause_count < 1:
            raise ValueError("detected coverage items must have clause_count >= 1")
        if not self.detected and self.clause_count != 0:
            raise ValueError("missing coverage items must have clause_count == 0")
        return self


class DocumentSummaryResponse(BaseModel):
    document_id: UUID
    document_version_id: UUID
    analysis_job_id: UUID | None = None
    generated_from_status: DocumentStatus
    overall_risk_score: int = Field(ge=0, le=100)
    top_issues: list[SummaryIssue]
    missing_protections: list[MissingProtectionSummary]
    negotiation_priorities: list[NegotiationPrioritySummary]
    clause_coverage_summary: list[ClauseCoverageItem]
    updated_at: datetime

    @model_validator(mode="after")
    def validate_priority_ranks(self):
        expected = list(range(1, len(self.negotiation_priorities) + 1))
        actual = [item.priority_rank for item in self.negotiation_priorities]
        if actual != expected:
            raise ValueError("negotiation priorities must be sequential starting at 1")
        return self


class DocumentDetailResponse(BaseModel):
    id: UUID
    filename: str
    status: DocumentStatus
    latest_version_number: int
    created_at: datetime
    updated_at: datetime
    current_job_status: JobStatus | None = None
    current_stage: str | None = None
    overall_risk_score: int | None = Field(default=None, ge=0, le=100)
