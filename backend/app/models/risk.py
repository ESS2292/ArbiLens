from sqlalchemy import CheckConstraint, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RiskScope, RiskSeverity
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Risk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risks"
    __table_args__ = (
        CheckConstraint(
            "(scope = 'document' AND clause_id IS NULL) OR (scope = 'clause' AND clause_id IS NOT NULL)",
            name="ck_risks_scope_clause_id",
        ),
    )

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    clause_id: Mapped[str | None] = mapped_column(ForeignKey("clauses.id"), nullable=True, index=True)
    analysis_job_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_jobs.id"), nullable=True, index=True)
    scope: Mapped[RiskScope] = mapped_column(
        Enum(RiskScope, name="risk_scope"),
        nullable=False,
        default=RiskScope.document,
        index=True,
    )
    severity: Mapped[RiskSeverity] = mapped_column(
        Enum(RiskSeverity, name="risk_severity"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    citations: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    deterministic_rule_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    document = relationship("Document", back_populates="risks")
    document_version = relationship("DocumentVersion", back_populates="risks")
    clause = relationship("Clause", back_populates="risks")
    analysis_job = relationship("AnalysisJob", back_populates="risks")
