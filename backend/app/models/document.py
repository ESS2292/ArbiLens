from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DocumentStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.uploaded,
        index=True,
    )
    latest_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    organization = relationship("Organization", back_populates="documents")
    created_by_user = relationship("User", back_populates="created_documents")
    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number",
    )
    risks = relationship("Risk", back_populates="document")
    analysis_jobs = relationship("AnalysisJob", back_populates="document")
    reports = relationship("Report", back_populates="document")
