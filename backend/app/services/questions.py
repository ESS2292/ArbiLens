"""Answer a question from the clause spans stored for an uploaded document."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.engine.embeddings import FakeEmbeddingProvider
from app.engine.llm import FakeLLMProvider
from app.engine.pipeline import ask_over_chunks
from app.engine.strategy import upgraded_strategy
from app.engine.types import Chunk, GroundedAnswer
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import DocumentStatus
from app.models.user import User


class DocumentQuestionService:
    """Ask a stored contract using the chunks the normalizer already saved."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def ask(self, *, document_id: UUID, current_user: User, question: str) -> GroundedAnswer:
        document = self._get_document(document_id=document_id, current_user=current_user)
        version = max(document.versions, key=lambda item: item.version_number)
        if document.status != DocumentStatus.completed or version.extracted_text is None or not version.chunks:
            raise AppError(
                "The document is not ready to answer questions.",
                status_code=409,
                code="document_not_ready",
            )
        text = version.extracted_text.full_text
        chunks: list[Chunk] = []
        for stored in sorted(version.chunks, key=lambda item: item.chunk_index):
            if stored.char_start is None or stored.char_end is None:
                raise AppError(
                    "Stored chunks are missing character offsets.",
                    status_code=409,
                    code="chunk_offsets_missing",
                )
            chunks.append(
                Chunk(
                    chunk_id=f"c{stored.chunk_index}",
                    text=stored.text,
                    char_start=stored.char_start,
                    char_end=stored.char_end,
                    section_title=stored.section_title,
                    strategy="clause_aware",
                )
            )
        return ask_over_chunks(
            text,
            chunks,
            question,
            upgraded_strategy(),
            embedder=FakeEmbeddingProvider(),
            llm=FakeLLMProvider(),
        )

    def _get_document(self, *, document_id: UUID, current_user: User) -> Document:
        document = self.session.scalar(
            select(Document)
            .options(
                selectinload(Document.versions).selectinload(DocumentVersion.chunks),
                selectinload(Document.versions).selectinload(DocumentVersion.extracted_text),
            )
            .where(Document.id == document_id, Document.organization_id == current_user.organization_id)
        )
        if document is None or not document.versions:
            raise AppError("Document not found.", status_code=404, code="document_not_found")
        return document
