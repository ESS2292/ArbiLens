from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DocumentStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_versions_number"),
    )

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    uploaded_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", create_type=False),
        nullable=False,
        default=DocumentStatus.uploaded,
        index=True,
    )

    document = relationship("Document", back_populates="versions")
    uploaded_by_user = relationship("User", back_populates="uploaded_versions")
    extracted_text = relationship(
        "ExtractedText",
        back_populates="document_version",
        cascade="all, delete-orphan",
        uselist=False,
    )
    chunks = relationship("DocumentChunk", back_populates="document_version", cascade="all, delete-orphan")
    clauses = relationship("Clause", back_populates="document_version", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="document_version")
    analysis_jobs = relationship("AnalysisJob", back_populates="document_version")
    reports = relationship("Report", back_populates="document_version")
