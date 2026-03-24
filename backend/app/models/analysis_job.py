from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import JobStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AnalysisJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analysis_jobs"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(
        ForeignKey("document_versions.id"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.queued,
        index=True,
    )
    task_name: Mapped[str] = mapped_column(String(255), nullable=False, default="document_pipeline")
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False, default="queued")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    organization = relationship("Organization", back_populates="analysis_jobs")
    document = relationship("Document", back_populates="analysis_jobs")
    document_version = relationship("DocumentVersion", back_populates="analysis_jobs")
    requested_by_user = relationship("User", back_populates="requested_jobs")
    risks = relationship("Risk", back_populates="analysis_job")
    reports = relationship("Report", back_populates="analysis_job")
