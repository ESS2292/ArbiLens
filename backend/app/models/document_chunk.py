from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_version_id", "chunk_index", name="uq_document_chunks_index"),
    )

    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    extracted_text_id: Mapped[str | None] = mapped_column(ForeignKey("extracted_text.id"), nullable=True, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document_version = relationship("DocumentVersion", back_populates="chunks")
    extracted_text = relationship("ExtractedText", back_populates="chunks")
    clauses = relationship("Clause", back_populates="chunk")
