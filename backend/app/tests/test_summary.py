from sqlalchemy.orm import Session

from app.schemas.risks import RiskRead
from app.schemas.summary import DocumentSummaryResponse
from app.models.analysis_job import AnalysisJob
from app.models.clause import Clause
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import ClauseType, DocumentStatus, JobStatus, OrganizationRole, RiskScope, RiskSeverity
from app.models.organization import Organization
from app.models.risk import Risk
from app.models.user import User
from app.services.summaries import DocumentSummaryService


def _build_document_with_analysis(db_session: Session) -> tuple[User, Document]:
    organization = Organization(name="Acme Summary", slug="acme-summary")
    user = User(
        organization=organization,
        email="summary@example.com",
        full_name="Summary Owner",
        password_hash="hashed",
        role=OrganizationRole.owner,
        is_active=True,
    )
    document = Document(
        organization=organization,
        created_by_user=user,
        filename="msa.pdf",
        status=DocumentStatus.completed,
        latest_version_number=1,
    )
    version = DocumentVersion(
        document=document,
        uploaded_by_user=user,
        version_number=1,
        storage_key="summary-key",
        original_filename="msa.pdf",
        content_type="application/pdf",
        file_extension=".pdf",
        file_size_bytes=100,
        sha256_hash="c" * 64,
        is_current=True,
        status=DocumentStatus.completed,
    )
    job = AnalysisJob(
        organization=organization,
        document=document,
        document_version=version,
        requested_by_user=user,
        status=JobStatus.completed,
        current_stage="completed",
    )
    clause = Clause(
        document_version=version,
        clause_type=ClauseType.limitation_of_liability,
        title="Limitation of Liability",
        text="Liability is unlimited.",
        normalized_text="Liability is unlimited.",
        confidence=0.9,
        source_method="heuristic",
        page_start=4,
        page_end=4,
    )
    db_session.add_all([organization, user, document, version, job, clause])
    db_session.flush()

    db_session.add_all(
        [
            Risk(
                document_id=document.id,
                document_version_id=version.id,
                clause_id=clause.id,
                analysis_job_id=job.id,
                scope=RiskScope.clause,
                severity=RiskSeverity.critical,
                category="liability",
                title="Potential uncapped liability",
                summary="Potential uncapped liability",
                score=95,
                rationale="Unlimited exposure detected.",
                recommendation="Cap liability.",
                confidence=0.88,
                citations=[
                    {
                        "reference_type": "clause",
                        "clause_id": str(clause.id),
                        "page_start": 4,
                        "page_end": 4,
                    }
                ],
                deterministic_rule_code="uncapped_liability",
                evidence_text=clause.text,
            ),
            Risk(
                document_id=document.id,
                document_version_id=version.id,
                clause_id=None,
                analysis_job_id=job.id,
                scope=RiskScope.document,
                severity=RiskSeverity.high,
                category="confidentiality",
                title="Missing confidentiality protections",
                summary="Missing confidentiality protections",
                score=72,
                rationale="No confidentiality clause was detected.",
                recommendation="Add confidentiality obligations.",
                confidence=0.75,
                citations=[{"reference_type": "document_context", "document_version_id": str(version.id)}],
                deterministic_rule_code="missing_confidentiality",
                evidence_text=None,
            ),
        ]
    )
    db_session.commit()
    return user, document


def test_document_summary_aggregates_risks_and_clause_coverage(db_session: Session) -> None:
    current_user, document = _build_document_with_analysis(db_session)

    summary = DocumentSummaryService(db_session).get_summary(
        document_id=document.id,
        current_user=current_user,
    )

    assert summary.overall_risk_score >= 80
    assert summary.top_issues[0].title == "Potential uncapped liability"
    assert summary.missing_protections[0].risk_id
    confidentiality_coverage = next(
        item for item in summary.clause_coverage_summary if item.clause_type == ClauseType.confidentiality
    )
    liability_coverage = next(
        item
        for item in summary.clause_coverage_summary
        if item.clause_type == ClauseType.limitation_of_liability
    )
    assert confidentiality_coverage.detected is False
    assert liability_coverage.detected is True


def test_summary_response_validates_and_preserves_citations(db_session: Session) -> None:
    current_user, document = _build_document_with_analysis(db_session)

    summary = DocumentSummaryService(db_session).get_summary(
        document_id=document.id,
        current_user=current_user,
    )
    payload = DocumentSummaryResponse.model_validate(summary).model_dump(mode="json")

    assert payload["top_issues"][0]["citations"]
    assert payload["top_issues"][0]["citations"][0]["reference_type"] in {"clause", "document_context"}


def test_summary_service_backfills_missing_document_level_citations(db_session: Session) -> None:
    current_user, document = _build_document_with_analysis(db_session)

    summary = DocumentSummaryService(db_session).get_summary(
        document_id=document.id,
        current_user=current_user,
    )

    missing_confidentiality = next(item for item in summary.top_issues if item.category == "confidentiality")
    assert missing_confidentiality.citations
    assert missing_confidentiality.citations[0].reference_type == "document_context"


def test_document_detail_includes_current_status_and_score(db_session: Session) -> None:
    current_user, document = _build_document_with_analysis(db_session)

    detail = DocumentSummaryService(db_session).get_document(
        document_id=document.id,
        current_user=current_user,
    )

    assert detail.status == DocumentStatus.completed
    assert detail.current_job_status == JobStatus.completed
    assert detail.overall_risk_score is not None


def test_risk_serialization_contract_uses_typed_citations(db_session: Session) -> None:
    current_user, document = _build_document_with_analysis(db_session)
    risks = DocumentSummaryService(db_session).get_risks(document_id=document.id, current_user=current_user)

    serialized = [RiskRead.model_validate(risk).model_dump(mode="json") for risk in risks]

    assert serialized[0]["citations"]
    assert serialized[0]["citations"][0]["page_start"] is not None or serialized[0]["citations"][0]["reference_type"] == "document_context"
