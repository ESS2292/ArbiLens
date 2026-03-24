from sqlalchemy.orm import Session

from app.models.analysis_job import AnalysisJob
from app.models.clause import Clause
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import ClauseType, DocumentStatus, JobStatus, OrganizationRole, RiskSeverity
from app.models.organization import Organization
from app.models.user import User
from app.schemas.ai import RiskExplanationSchema
from app.services.scoring import DeterministicRiskScoringService


class _FakeAIService:
    def generate_structured_output(self, **_: object) -> RiskExplanationSchema:
        return RiskExplanationSchema(
            summary="AI explanation",
            rationale="Deterministic score explained",
            recommendation="Negotiate balanced language",
            confidence=0.84,
        )


def _build_version_with_clauses(db_session: Session) -> tuple[DocumentVersion, AnalysisJob]:
    organization = Organization(name="Acme", slug="acme-score")
    user = User(
        organization=organization,
        email="owner+score@example.com",
        full_name="Owner",
        password_hash="hashed",
        role=OrganizationRole.owner,
        is_active=True,
    )
    document = Document(
        organization=organization,
        created_by_user=user,
        filename="msa.pdf",
        status=DocumentStatus.analyzing,
        latest_version_number=1,
    )
    version = DocumentVersion(
        document=document,
        uploaded_by_user=user,
        version_number=1,
        storage_key="score-key",
        original_filename="msa.pdf",
        content_type="application/pdf",
        file_extension=".pdf",
        file_size_bytes=120,
        sha256_hash="b" * 64,
        is_current=True,
        status=DocumentStatus.analyzing,
    )
    job = AnalysisJob(
        organization=organization,
        document=document,
        document_version=version,
        requested_by_user=user,
        status=JobStatus.analyzing,
        current_stage="analyzing_risks",
    )
    db_session.add_all([organization, user, document, version, job])
    db_session.flush()
    return version, job


def test_risk_rubric_flags_uncapped_liability_as_critical(db_session: Session) -> None:
    version, job = _build_version_with_clauses(db_session)
    clause = Clause(
        document_version_id=version.id,
        clause_type=ClauseType.limitation_of_liability,
        title="Limitation of Liability",
        text="Supplier liability is unlimited and without limitation.",
        normalized_text="Supplier liability is unlimited and without limitation.",
        confidence=0.9,
        source_method="heuristic",
        page_start=5,
        page_end=5,
    )
    db_session.add(clause)
    db_session.flush()

    risks = DeterministicRiskScoringService(db_session, ai_service=_FakeAIService()).analyze_and_persist(version, job.id)
    liability_risk = next(risk for risk in risks if risk.category == "liability")

    assert liability_risk.severity == RiskSeverity.critical
    assert liability_risk.score == 95


def test_risk_scoring_aggregates_multiple_findings(db_session: Session) -> None:
    version, job = _build_version_with_clauses(db_session)
    db_session.add_all(
        [
            Clause(
                document_version_id=version.id,
                clause_type=ClauseType.indemnification,
                title="Indemnity",
                text="Customer shall indemnify provider against all claims.",
                normalized_text="Customer shall indemnify provider against all claims.",
                confidence=0.9,
                source_method="heuristic",
                page_start=2,
                page_end=2,
            ),
            Clause(
                document_version_id=version.id,
                clause_type=ClauseType.termination,
                title="Termination",
                text="Provider may terminate for convenience at any time.",
                normalized_text="Provider may terminate for convenience at any time.",
                confidence=0.9,
                source_method="heuristic",
                page_start=3,
                page_end=3,
            ),
        ]
    )
    db_session.flush()

    risks = DeterministicRiskScoringService(db_session, ai_service=_FakeAIService()).analyze_and_persist(version, job.id)

    categories = {risk.category for risk in risks}
    assert "indemnity" in categories
    assert "termination" in categories
    assert "confidentiality" in categories


def test_document_scope_risks_receive_document_context_citations(db_session: Session) -> None:
    version, job = _build_version_with_clauses(db_session)

    risks = DeterministicRiskScoringService(db_session, ai_service=_FakeAIService()).analyze_and_persist(version, job.id)
    confidentiality_risk = next(risk for risk in risks if risk.category == "confidentiality")

    assert confidentiality_risk.citations
    assert confidentiality_risk.citations[0]["reference_type"] == "document_context"


def test_ai_narrative_cannot_override_deterministic_recommendation_or_score(db_session: Session) -> None:
    class _AggressiveAIService:
        def generate_structured_output(self, **_: object) -> RiskExplanationSchema:
            return RiskExplanationSchema(
                summary="AI summary only",
                rationale="Different rationale",
                recommendation="AI says ignore this risk completely",
                confidence=0.93,
            )

    version, job = _build_version_with_clauses(db_session)
    clause = Clause(
        document_version_id=version.id,
        clause_type=ClauseType.limitation_of_liability,
        title="Limitation of Liability",
        text="Supplier liability is unlimited and without limitation.",
        normalized_text="Supplier liability is unlimited and without limitation.",
        confidence=0.9,
        source_method="heuristic",
        page_start=5,
        page_end=5,
    )
    db_session.add(clause)
    db_session.flush()

    risks = DeterministicRiskScoringService(db_session, ai_service=_AggressiveAIService()).analyze_and_persist(
        version,
        job.id,
    )
    liability_risk = next(risk for risk in risks if risk.category == "liability")

    assert liability_risk.summary == "AI summary only"
    assert liability_risk.score == 95
    assert liability_risk.rationale == "The liability language appears to allow uncapped or open-ended exposure."
    assert liability_risk.recommendation == "Cap liability to a negotiated multiple of fees and carve out only limited exceptions."
