from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_status: Mapped[str] = mapped_column(String(64), nullable=False, default="inactive")
    subscription_current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    users = relationship("User", back_populates="organization")
    documents = relationship("Document", back_populates="organization")
    analysis_jobs = relationship("AnalysisJob", back_populates="organization")
    reports = relationship("Report", back_populates="organization")
