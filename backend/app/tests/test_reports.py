from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.analysis_job import AnalysisJob
from app.models.clause import Clause
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import ClauseType, DocumentStatus, JobStatus, RiskScope, RiskSeverity
from app.models.risk import Risk
from app.models.user import User
from app.tests.conftest import register_user


def _build_completed_document(db_session: Session, user: User, filename: str = "msa.pdf") -> Document:
    organization = user.organization
    organization.stripe_subscription_status = "active"

    document = Document(
        organization=organization,
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
        file_size_bytes=128,
        sha256_hash="d" * 64,
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
        text="Liability is uncapped.",
        normalized_text="Liability is uncapped.",
        confidence=0.95,
        source_method="heuristic",
        page_start=2,
        page_end=2,
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
            severity=RiskSeverity.critical,
            category="liability",
            title="Potential uncapped liability",
            summary="Potential uncapped liability",
            score=92,
            rationale="The limitation of liability clause does not cap exposure.",
            recommendation="Insert a monetary cap and carve-outs.",
            confidence=0.9,
            citations=[
                {
                    "reference_type": "clause",
                    "clause_id": str(clause.id),
                    "page_start": 2,
                    "page_end": 2,
                }
            ],
            deterministic_rule_code="uncapped_liability",
            evidence_text=clause.text,
        )
    )
    db_session.commit()
    db_session.refresh(document)
    return document


def test_generate_report_persists_metadata_and_returns_download_url(
    client: TestClient,
    db_session: Session,
) -> None:
    registered = register_user(client)
    token = registered["access_token"]
    user = db_session.query(User).filter_by(email="alex@example.com").one()
    document = _build_completed_document(db_session, user)

    response = client.post(
        f"/api/v1/reports/documents/{document.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["report"]["status"] == "generated"
    assert payload["report"]["file_size_bytes"] > 0
    assert payload["download_url"].startswith("https://storage.local/")

    listing = client.get(
        f"/api/v1/reports/documents/{document.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_report_generation_requires_active_subscription(client: TestClient, db_session: Session) -> None:
    registered = register_user(client)
    token = registered["access_token"]
    user = db_session.query(User).filter_by(email="alex@example.com").one()
    document = _build_completed_document(db_session, user, filename="vendor.pdf")
    user.organization.stripe_subscription_status = "inactive"
    db_session.commit()

    response = client.post(
        f"/api/v1/reports/documents/{document.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 402
    assert response.json()["error"]["code"] == "premium_required"
