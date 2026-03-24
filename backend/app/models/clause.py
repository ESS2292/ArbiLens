from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ClauseType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Clause(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clauses"

    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    chunk_id: Mapped[str | None] = mapped_column(ForeignKey("document_chunks.id"), nullable=True, index=True)
    clause_type: Mapped[ClauseType] = mapped_column(
        Enum(ClauseType, name="clause_type"),
        nullable=False,
        default=ClauseType.general,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_method: Mapped[str] = mapped_column(String(32), nullable=False, default="heuristic")
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_char: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document_version = relationship("DocumentVersion", back_populates="clauses")
    chunk = relationship("DocumentChunk", back_populates="clauses")
    risks = relationship("Risk", back_populates="clause")
