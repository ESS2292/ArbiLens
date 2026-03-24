from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.enums import ClauseType, DocumentStatus, JobStatus, OrganizationRole
from app.models.organization import Organization
from app.models.user import User
from app.models.analysis_job import AnalysisJob
from app.schemas.ai import ClauseExtractionResponseSchema
from app.services.extraction import ClauseExtractionService


class _FakeAIService:
    def __init__(self, response: ClauseExtractionResponseSchema) -> None:
        self.response = response

    def generate_structured_output(self, **_: object) -> ClauseExtractionResponseSchema:
        return self.response


class _FailingAIService:
    def generate_structured_output(self, **_: object) -> ClauseExtractionResponseSchema:
        raise AppError("Malformed AI output.", status_code=502, code="ai_schema_validation_failed")


def _build_version_graph(db_session: Session) -> DocumentVersion:
    organization = Organization(name="Acme", slug="acme")
    user = User(
        organization=organization,
        email="owner@example.com",
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
        storage_key="key",
        original_filename="msa.pdf",
        content_type="application/pdf",
        file_extension=".pdf",
        file_size_bytes=123,
        sha256_hash="a" * 64,
        is_current=True,
        status=DocumentStatus.analyzing,
    )
    job = AnalysisJob(
        organization=organization,
        document=document,
        document_version=version,
        requested_by_user=user,
        status=JobStatus.analyzing,
        current_stage="extracting_clauses",
    )
    db_session.add_all([organization, user, document, version, job])
    db_session.flush()
    return version


def test_heuristic_clause_detection_finds_heading_markers(db_session: Session) -> None:
    version = _build_version_graph(db_session)
    chunk = DocumentChunk(
        document_version_id=version.id,
        chunk_index=0,
        section_title="Limitation of Liability",
        page_start=4,
        page_end=4,
        text="Limitation of Liability\nNeither party will be liable for indirect damages.",
        token_count=20,
        char_count=75,
        char_start=0,
        char_end=75,
    )
    db_session.add(chunk)
    db_session.flush()

    clauses = ClauseExtractionService(db_session, ai_service=_FakeAIService(ClauseExtractionResponseSchema(clauses=[]))).extract_and_persist(version)

    assert len(clauses) == 1
    assert clauses[0].clause_type == ClauseType.limitation_of_liability
    assert clauses[0].source_method == "heuristic"


def test_ai_clause_detection_handles_ambiguous_chunks(db_session: Session) -> None:
    version = _build_version_graph(db_session)
    chunk = DocumentChunk(
        document_version_id=version.id,
        chunk_index=1,
        section_title="Commercial Terms",
        page_start=2,
        page_end=2,
        text="All disagreements must be submitted to a neutral decision maker selected by the provider in New York.",
        token_count=14,
        char_count=96,
        char_start=0,
        char_end=96,
    )
    db_session.add(chunk)
    db_session.flush()

    ai_response = ClauseExtractionResponseSchema.model_validate(
        {
            "clauses": [
                {
                    "clause_type": "dispute_resolution",
                    "title": "Dispute Resolution",
                    "extracted_text": chunk.text,
                    "confidence": 0.77,
                    "source_chunk_index": 1,
                    "page_start": 2,
                    "page_end": 2,
                }
            ]
        }
    )
    clauses = ClauseExtractionService(db_session, ai_service=_FakeAIService(ai_response)).extract_and_persist(version)

    assert len(clauses) == 1
    assert clauses[0].clause_type == ClauseType.dispute_resolution
    assert clauses[0].source_method == "ai"


def test_malformed_ai_clause_output_does_not_fail_extraction(db_session: Session) -> None:
    version = _build_version_graph(db_session)
    chunk = DocumentChunk(
        document_version_id=version.id,
        chunk_index=2,
        section_title="Commercial Terms",
        page_start=2,
        page_end=2,
        text="The parties will discuss disputes in good faith before escalation.",
        token_count=12,
        char_count=69,
        char_start=0,
        char_end=69,
    )
    db_session.add(chunk)
    db_session.flush()

    clauses = ClauseExtractionService(db_session, ai_service=_FailingAIService()).extract_and_persist(version)

    assert clauses == []


def test_ai_clause_candidate_must_be_grounded_in_source_chunk(db_session: Session) -> None:
    version = _build_version_graph(db_session)
    chunk = DocumentChunk(
        document_version_id=version.id,
        chunk_index=3,
        section_title="Commercial Terms",
        page_start=2,
        page_end=2,
        text="The parties will discuss disputes in good faith before escalation.",
        token_count=12,
        char_count=69,
        char_start=0,
        char_end=69,
    )
    db_session.add(chunk)
    db_session.flush()

    ai_response = ClauseExtractionResponseSchema.model_validate(
        {
            "clauses": [
                {
                    "clause_type": "dispute_resolution",
                    "title": "Dispute Resolution",
                    "extracted_text": "This text does not exist in the chunk.",
                    "confidence": 0.8,
                    "source_chunk_index": 3,
                    "page_start": 2,
                    "page_end": 2,
                }
            ]
        }
    )

    clauses = ClauseExtractionService(db_session, ai_service=_FakeAIService(ai_response)).extract_and_persist(version)

    assert clauses == []


def test_ai_clause_candidate_with_wrong_chunk_index_is_discarded(db_session: Session) -> None:
    version = _build_version_graph(db_session)
    chunk = DocumentChunk(
        document_version_id=version.id,
        chunk_index=4,
        section_title="Confidentiality",
        page_start=3,
        page_end=3,
        text="Confidential information must not be disclosed.",
        token_count=10,
        char_count=47,
        char_start=0,
        char_end=47,
    )
    db_session.add(chunk)
    db_session.flush()

    ai_response = ClauseExtractionResponseSchema.model_validate(
        {
            "clauses": [
                {
                    "clause_type": "confidentiality",
                    "title": "Confidentiality",
                    "extracted_text": "Confidential information must not be disclosed.",
                    "confidence": 0.8,
                    "source_chunk_index": 999,
                    "page_start": 3,
                    "page_end": 3,
                }
            ]
        }
    )

    clauses = ClauseExtractionService(db_session, ai_service=_FakeAIService(ai_response)).extract_and_persist(version)

    assert clauses == []
