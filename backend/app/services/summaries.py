from collections import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models.analysis_job import AnalysisJob
from app.models.clause import Clause
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import ClauseType, RiskSeverity
from app.models.risk import Risk
from app.models.user import User
from app.schemas.references import SourceCitation
from app.schemas.summary import (
    ClauseCoverageItem,
    DocumentDetailResponse,
    DocumentSummaryResponse,
    MissingProtectionSummary,
    NegotiationPrioritySummary,
    SummaryIssue,
)

CLAUSE_COVERAGE_ORDER = [
    ClauseType.indemnification,
    ClauseType.limitation_of_liability,
    ClauseType.termination,
    ClauseType.auto_renewal,
    ClauseType.confidentiality,
    ClauseType.assignment,
    ClauseType.payment_terms,
    ClauseType.dispute_resolution,
    ClauseType.governing_law,
    ClauseType.ip_ownership,
    ClauseType.data_protection,
    ClauseType.warranties,
    ClauseType.force_majeure,
    ClauseType.sla,
    ClauseType.audit_rights,
]


class DocumentSummaryService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_document(self, *, document_id, current_user: User) -> DocumentDetailResponse:
        document = self._get_document(document_id=document_id, current_user=current_user)
        latest_job = self._latest_job(document)
        summary = self._build_summary(document)
        return DocumentDetailResponse(
            id=document.id,
            filename=document.filename,
            status=document.status,
            latest_version_number=document.latest_version_number,
            created_at=document.created_at,
            updated_at=document.updated_at,
            current_job_status=latest_job.status if latest_job else None,
            current_stage=latest_job.current_stage if latest_job else None,
            overall_risk_score=summary.overall_risk_score if summary else None,
        )

    def get_summary(self, *, document_id, current_user: User) -> DocumentSummaryResponse:
        document = self._get_document(document_id=document_id, current_user=current_user)
        summary = self._build_summary(document)
        if summary is None:
            raise AppError(
                "Document summary is not available until analysis completes.",
                status_code=409,
                code="summary_not_ready",
            )
        return summary

    def get_clauses(self, *, document_id, current_user: User) -> list[Clause]:
        document = self._get_document(document_id=document_id, current_user=current_user)
        version = self._latest_version(document)
        return sorted(version.clauses, key=lambda clause: (clause.page_start or 0, clause.created_at))

    def get_risks(self, *, document_id, current_user: User) -> list[Risk]:
        document = self._get_document(document_id=document_id, current_user=current_user)
        version = self._latest_version(document)
        severity_rank = {
            RiskSeverity.critical: 4,
            RiskSeverity.high: 3,
            RiskSeverity.medium: 2,
            RiskSeverity.low: 1,
        }
        return sorted(
            version.risks,
            key=lambda risk: (severity_rank[risk.severity], risk.score, risk.created_at),
            reverse=True,
        )

    def _get_document(self, *, document_id, current_user: User) -> Document:
        document = self.session.scalar(
            select(Document)
            .options(
                selectinload(Document.versions).selectinload(DocumentVersion.clauses),
                selectinload(Document.versions).selectinload(DocumentVersion.risks),
                selectinload(Document.analysis_jobs),
            )
            .where(
                Document.id == document_id,
                Document.organization_id == current_user.organization_id,
            )
        )
        if document is None:
            raise AppError("Document not found.", status_code=404, code="document_not_found")
        return document

    def _latest_version(self, document: Document) -> DocumentVersion:
        if not document.versions:
            raise AppError("Document version not found.", status_code=404, code="document_version_not_found")
        return max(document.versions, key=lambda version: version.version_number)

    def _latest_job(self, document: Document) -> AnalysisJob | None:
        if not document.analysis_jobs:
            return None
        return max(document.analysis_jobs, key=lambda job: job.created_at)

    def _build_summary(self, document: Document) -> DocumentSummaryResponse | None:
        version = self._latest_version(document)
        if not version.risks and not version.clauses:
            return None

        latest_job = self._latest_job(document)
        severity_rank = {
            RiskSeverity.critical: 4,
            RiskSeverity.high: 3,
            RiskSeverity.medium: 2,
            RiskSeverity.low: 1,
        }
        sorted_risks = sorted(
            version.risks,
            key=lambda risk: (severity_rank[risk.severity], risk.score, risk.created_at),
            reverse=True,
        )
        overall_risk_score = self._overall_risk_score(sorted_risks)

        top_issues = [
            SummaryIssue(
                risk_id=risk.id,
                category=risk.category,
                title=risk.title,
                severity=risk.severity,
                score=risk.score,
                rationale=risk.rationale,
                recommendation=risk.recommendation,
                clause_id=risk.clause_id,
                citations=self._normalize_citations(document=document, version=version, risk=risk),
            )
            for risk in sorted_risks[:5]
        ]

        missing_protections = [
            MissingProtectionSummary(
                category=risk.category,
                title=risk.title,
                risk_id=risk.id,
                recommendation=risk.recommendation,
            )
            for risk in sorted_risks
            if risk.deterministic_rule_code and risk.deterministic_rule_code.startswith("missing_")
        ][:5]

        negotiation_priorities = [
            NegotiationPrioritySummary(
                priority_rank=index + 1,
                risk_id=risk.id,
                title=risk.title,
                category=risk.category,
                recommendation=risk.recommendation,
                severity=risk.severity,
            )
            for index, risk in enumerate(sorted_risks[:5])
        ]

        clause_type_counts = Counter(clause.clause_type for clause in version.clauses)
        clause_ids_by_type: dict[ClauseType, list] = {}
        for clause in version.clauses:
            clause_ids_by_type.setdefault(clause.clause_type, []).append(clause.id)

        coverage = [
            ClauseCoverageItem(
                clause_type=clause_type,
                detected=clause_type_counts.get(clause_type, 0) > 0,
                clause_count=clause_type_counts.get(clause_type, 0),
                clause_ids=clause_ids_by_type.get(clause_type, []),
            )
            for clause_type in CLAUSE_COVERAGE_ORDER
        ]

        updated_at = max(
            [document.updated_at, version.updated_at, *(risk.updated_at for risk in version.risks)],
            default=document.updated_at,
        )
        return DocumentSummaryResponse(
            document_id=document.id,
            document_version_id=version.id,
            analysis_job_id=latest_job.id if latest_job else None,
            generated_from_status=document.status,
            overall_risk_score=overall_risk_score,
            top_issues=top_issues,
            missing_protections=missing_protections,
            negotiation_priorities=negotiation_priorities,
            clause_coverage_summary=coverage,
            updated_at=updated_at,
        )

    def _overall_risk_score(self, risks: list[Risk]) -> int:
        if not risks:
            return 0
        top_scores = sorted((risk.score for risk in risks), reverse=True)[:5]
        weighted_average = round(sum(top_scores) / len(top_scores))
        severity_bonus = 5 if any(risk.severity == RiskSeverity.critical for risk in risks) else 0
        return min(100, weighted_average + severity_bonus)

    def _normalize_citations(
        self,
        *,
        document: Document,
        version: DocumentVersion,
        risk: Risk,
    ) -> list[SourceCitation]:
        if risk.citations:
            return [SourceCitation.model_validate(citation) for citation in risk.citations]

        if risk.clause is not None:
            return [
                SourceCitation(
                    reference_type="clause",
                    clause_id=str(risk.clause.id),
                    chunk_id=str(risk.clause.chunk_id) if risk.clause.chunk_id else None,
                    page_start=risk.clause.page_start,
                    page_end=risk.clause.page_end,
                )
            ]

        return [
            SourceCitation(
                reference_type="document_context",
                document_version_id=str(version.id),
            )
        ]
