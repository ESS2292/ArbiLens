from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ExtractedText(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "extracted_text"

    document_version_id: Mapped[str] = mapped_column(
        ForeignKey("document_versions.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    parser_used: Mapped[str] = mapped_column(String(255), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_needed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    structured_representation: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    extractor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    document_version = relationship("DocumentVersion", back_populates="extracted_text")
    chunks = relationship("DocumentChunk", back_populates="extracted_text")
