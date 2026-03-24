from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.analysis_job import AnalysisJob
from app.models.clause import Clause
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import ClauseType, DocumentStatus, JobStatus, RiskScope, RiskSeverity
from app.models.user import User
from app.models.risk import Risk
from app.tests.conftest import register_user


def _seed_analyzed_document(
    db_session: Session,
    *,
    user: User,
    filename: str,
    clause_type: ClauseType,
    clause_text: str,
    risk_title: str,
    risk_score: int,
    risk_severity: RiskSeverity,
    risk_rule: str,
) -> Document:
    user.organization.stripe_subscription_status = "active"
    document = Document(
        organization=user.organization,
        created_by_user=user,
        filename=filename,
        status=DocumentStatus.completed,
        latest_version_number=1,
    )
    version = DocumentVersion(
        document=document,
        uploaded_by_user=user,
        version_number=1,
        storage_key=f"documents/{filename}",
        original_filename=filename,
        content_type="application/pdf",
        file_extension=".pdf",
        file_size_bytes=120,
        sha256_hash=(filename[0] * 64)[:64],
        is_current=True,
        status=DocumentStatus.completed,
    )
    job = AnalysisJob(
        organization=user.organization,
        document=document,
        document_version=version,
        requested_by_user=user,
        status=JobStatus.completed,
        current_stage="completed",
    )
    clause = Clause(
        document_version=version,
        clause_type=clause_type,
        title=clause_type.value.replace("_", " ").title(),
        text=clause_text,
        normalized_text=clause_text,
        confidence=0.94,
        source_method="heuristic",
        page_start=1,
        page_end=1,
    )
    db_session.add_all([document, version, job, clause])
    db_session.flush()
    db_session.add(
        Risk(
            document=document,
            document_version=version,
            clause=clause,
            analysis_job=job,
            scope=RiskScope.clause,
            severity=risk_severity,
            category="contract",
            title=risk_title,
            summary=risk_title,
            score=risk_score,
            rationale=f"{risk_title} rationale",
            recommendation="Negotiate improved terms.",
            confidence=0.82,
            citations=[
                {
                    "reference_type": "clause",
                    "clause_id": str(clause.id),
                    "page_start": 1,
                    "page_end": 1,
                }
            ],
            deterministic_rule_code=risk_rule,
            evidence_text=clause_text,
        )
    )
    db_session.commit()
    db_session.refresh(document)
    return document


def test_compare_documents_reports_clause_and_risk_changes(client: TestClient, db_session: Session) -> None:
    registered = register_user(client)
    token = registered["access_token"]
    user = db_session.query(User).filter_by(email="alex@example.com").one()

    left = _seed_analyzed_document(
        db_session,
        user=user,
        filename="left.pdf",
        clause_type=ClauseType.confidentiality,
        clause_text="Each party shall keep information confidential.",
        risk_title="Weak confidentiality language",
        risk_score=30,
        risk_severity=RiskSeverity.medium,
        risk_rule="weak_confidentiality",
    )
    right = _seed_analyzed_document(
        db_session,
        user=user,
        filename="right.pdf",
        clause_type=ClauseType.assignment,
        clause_text="Vendor may assign this agreement without consent.",
        risk_title="Unilateral assignment right",
        risk_score=68,
        risk_severity=RiskSeverity.high,
        risk_rule="unilateral_assignment",
    )

    response = client.get(
        f"/api/v1/comparisons/documents?left_document_id={left.id}&right_document_id={right.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["score_delta"] > 0
    assert "confidentiality" in payload["protections_removed"]
    assert "assignment" in payload["protections_added"]
    assert any(item["change_type"] == "new_risk" for item in payload["new_risks_introduced"])
