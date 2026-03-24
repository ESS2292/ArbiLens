from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.analysis_job import AnalysisJob
from app.models.clause import Clause
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import ClauseType, DocumentStatus, JobStatus, RiskScope, RiskSeverity
from app.models.risk import Risk
from app.models.user import User
from app.schemas.clauses import ClauseRead
from app.schemas.risks import RiskRead
from app.schemas.summary import DocumentSummaryResponse
from app.tests.conftest import register_user


def _seed_completed_document(db_session: Session, user: User) -> Document:
    document = Document(
        organization=user.organization,
        created_by_user=user,
        filename="msa.pdf",
        status=DocumentStatus.completed,
        latest_version_number=1,
    )
    version = DocumentVersion(
        document=document,
        uploaded_by_user=user,
        version_number=1,
        storage_key="api-contract-key",
        original_filename="msa.pdf",
        content_type="application/pdf",
        file_extension=".pdf",
        file_size_bytes=100,
        sha256_hash="f" * 64,
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
        clause_type=ClauseType.limitation_of_liability,
        title="Limitation of Liability",
        text="Liability is unlimited.",
        normalized_text="Liability is unlimited.",
        confidence=0.9,
        source_method="heuristic",
        page_start=4,
        page_end=4,
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
        )
    )
    db_session.commit()
    db_session.refresh(document)
    return document


def test_document_api_payloads_match_declared_schemas(client: TestClient, db_session: Session) -> None:
    registered = register_user(client)
    token = registered["access_token"]
    user = db_session.query(User).filter_by(email="alex@example.com").one()
    document = _seed_completed_document(db_session, user)

    summary_response = client.get(
        f"/api/v1/documents/{document.id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    risks_response = client.get(
        f"/api/v1/documents/{document.id}/risks",
        headers={"Authorization": f"Bearer {token}"},
    )
    clauses_response = client.get(
        f"/api/v1/documents/{document.id}/clauses",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert summary_response.status_code == 200
    assert risks_response.status_code == 200
    assert clauses_response.status_code == 200

    DocumentSummaryResponse.model_validate(summary_response.json())
    [RiskRead.model_validate(item) for item in risks_response.json()]
    [ClauseRead.model_validate(item) for item in clauses_response.json()]
