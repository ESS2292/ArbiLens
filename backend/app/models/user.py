from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import OrganizationRole
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_users_org_email"),)

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[OrganizationRole] = mapped_column(
        Enum(OrganizationRole, name="organization_role"),
        nullable=False,
        default=OrganizationRole.member,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization = relationship("Organization", back_populates="users")
    created_documents = relationship("Document", back_populates="created_by_user")
    uploaded_versions = relationship("DocumentVersion", back_populates="uploaded_by_user")
    requested_jobs = relationship("AnalysisJob", back_populates="requested_by_user")
    created_reports = relationship("Report", back_populates="created_by_user")
