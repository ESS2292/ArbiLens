from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), nullable=True, index=True)
    analysis_job_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_jobs.id"), nullable=True, index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False, default="pdf")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="generated")
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="reports")
    document = relationship("Document", back_populates="reports")
    document_version = relationship("DocumentVersion", back_populates="reports")
    analysis_job = relationship("AnalysisJob", back_populates="reports")
    created_by_user = relationship("User", back_populates="created_reports")
