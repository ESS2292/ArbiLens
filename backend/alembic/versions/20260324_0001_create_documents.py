"""create initial core schema

Revision ID: 20260324_0001
Revises: 
Create Date: 2026-03-24 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
# revision identifiers, used by Alembic.
revision: str = "20260324_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


organization_role = sa.Enum("owner", "admin", "member", name="organization_role")
document_status = sa.Enum(
    "uploaded",
    "queued",
    "parsing",
    "parsed",
    "analyzing",
    "analyzed",
    "completed",
    "failed",
    name="document_status",
)
job_status = sa.Enum("queued", "parsing", "parsed", "analyzing", "completed", "failed", name="job_status")
risk_severity = sa.Enum("low", "medium", "high", "critical", name="risk_severity")
clause_type = sa.Enum(
    "indemnification",
    "limitation_of_liability",
    "termination",
    "confidentiality",
    "auto_renewal",
    "assignment",
    "payment_terms",
    "dispute_resolution",
    "governing_law",
    "ip_ownership",
    "data_protection",
    "warranties",
    "force_majeure",
    "sla",
    "audit_rights",
    "general",
    name="clause_type",
)
risk_scope = sa.Enum("document", "clause", name="risk_scope")


def upgrade() -> None:
    organization_role.create(op.get_bind(), checkfirst=True)
    document_status.create(op.get_bind(), checkfirst=True)
    job_status.create(op.get_bind(), checkfirst=True)
    risk_severity.create(op.get_bind(), checkfirst=True)
    clause_type.create(op.get_bind(), checkfirst=True)
    risk_scope.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_status", sa.String(length=64), nullable=False),
        sa.Column("subscription_current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)
    op.create_index(op.f("ix_organizations_stripe_customer_id"), "organizations", ["stripe_customer_id"], unique=False)
    op.create_index(op.f("ix_organizations_stripe_subscription_id"), "organizations", ["stripe_subscription_id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", organization_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("organization_id", "email", name="uq_users_org_email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("status", document_status, nullable=False),
        sa.Column("latest_version_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_created_by_user_id"), "documents", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_documents_organization_id"), "documents", ["organization_id"], unique=False)
    op.create_index(op.f("ix_documents_status"), "documents", ["status"], unique=False)

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("file_extension", sa.String(length=16), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("status", document_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_versions_number"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(op.f("ix_document_versions_document_id"), "document_versions", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_versions_is_current"), "document_versions", ["is_current"], unique=False)
    op.create_index(op.f("ix_document_versions_sha256_hash"), "document_versions", ["sha256_hash"], unique=False)
    op.create_index(op.f("ix_document_versions_status"), "document_versions", ["status"], unique=False)
    op.create_index(op.f("ix_document_versions_uploaded_by_user_id"), "document_versions", ["uploaded_by_user_id"], unique=False)

    op.create_table(
        "extracted_text",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("parser_used", sa.String(length=255), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("ocr_needed", sa.Boolean(), nullable=False),
        sa.Column("structured_representation", sa.JSON(), nullable=False),
        sa.Column("extractor_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_version_id"),
    )
    op.create_index(op.f("ix_extracted_text_document_version_id"), "extracted_text", ["document_version_id"], unique=True)

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("extracted_text_id", sa.Uuid(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section_title", sa.String(length=255), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["extracted_text_id"], ["extracted_text.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_version_id", "chunk_index", name="uq_document_chunks_index"),
    )
    op.create_index(op.f("ix_document_chunks_document_version_id"), "document_chunks", ["document_version_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_extracted_text_id"), "document_chunks", ["extracted_text_id"], unique=False)

    op.create_table(
        "clauses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("clause_type", clause_type, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_method", sa.String(length=32), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("start_char", sa.Integer(), nullable=True),
        sa.Column("end_char", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clauses_chunk_id"), "clauses", ["chunk_id"], unique=False)
    op.create_index(op.f("ix_clauses_clause_type"), "clauses", ["clause_type"], unique=False)
    op.create_index(op.f("ix_clauses_document_version_id"), "clauses", ["document_version_id"], unique=False)

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("error_stage", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_transitioned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_jobs_document_id"), "analysis_jobs", ["document_id"], unique=False)
    op.create_index(op.f("ix_analysis_jobs_document_version_id"), "analysis_jobs", ["document_version_id"], unique=False)
    op.create_index(op.f("ix_analysis_jobs_organization_id"), "analysis_jobs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_analysis_jobs_requested_by_user_id"), "analysis_jobs", ["requested_by_user_id"], unique=False)
    op.create_index(op.f("ix_analysis_jobs_status"), "analysis_jobs", ["status"], unique=False)

    op.create_table(
        "risks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("clause_id", sa.Uuid(), nullable=True),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=True),
        sa.Column("scope", risk_scope, nullable=False),
        sa.Column("severity", risk_severity, nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("deterministic_rule_code", sa.String(length=128), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(scope = 'document' AND clause_id IS NULL) OR (scope = 'clause' AND clause_id IS NOT NULL)",
            name="ck_risks_scope_clause_id",
        ),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["clause_id"], ["clauses.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risks_analysis_job_id"), "risks", ["analysis_job_id"], unique=False)
    op.create_index(op.f("ix_risks_category"), "risks", ["category"], unique=False)
    op.create_index(op.f("ix_risks_clause_id"), "risks", ["clause_id"], unique=False)
    op.create_index(op.f("ix_risks_document_id"), "risks", ["document_id"], unique=False)
    op.create_index(op.f("ix_risks_document_version_id"), "risks", ["document_version_id"], unique=False)
    op.create_index(op.f("ix_risks_scope"), "risks", ["scope"], unique=False)
    op.create_index(op.f("ix_risks_severity"), "risks", ["severity"], unique=False)

    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=True),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(op.f("ix_reports_analysis_job_id"), "reports", ["analysis_job_id"], unique=False)
    op.create_index(op.f("ix_reports_created_by_user_id"), "reports", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_reports_document_id"), "reports", ["document_id"], unique=False)
    op.create_index(op.f("ix_reports_document_version_id"), "reports", ["document_version_id"], unique=False)
    op.create_index(op.f("ix_reports_organization_id"), "reports", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_organization_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_document_version_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_document_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_created_by_user_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_analysis_job_id"), table_name="reports")
    op.drop_table("reports")

    op.drop_index(op.f("ix_risks_severity"), table_name="risks")
    op.drop_index(op.f("ix_risks_scope"), table_name="risks")
    op.drop_index(op.f("ix_risks_document_version_id"), table_name="risks")
    op.drop_index(op.f("ix_risks_document_id"), table_name="risks")
    op.drop_index(op.f("ix_risks_category"), table_name="risks")
    op.drop_index(op.f("ix_risks_clause_id"), table_name="risks")
    op.drop_index(op.f("ix_risks_analysis_job_id"), table_name="risks")
    op.drop_table("risks")

    op.drop_index(op.f("ix_analysis_jobs_status"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_requested_by_user_id"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_organization_id"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_document_version_id"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_document_id"), table_name="analysis_jobs")
    op.drop_table("analysis_jobs")

    op.drop_index(op.f("ix_clauses_document_version_id"), table_name="clauses")
    op.drop_index(op.f("ix_clauses_clause_type"), table_name="clauses")
    op.drop_index(op.f("ix_clauses_chunk_id"), table_name="clauses")
    op.drop_table("clauses")

    op.drop_index(op.f("ix_document_chunks_extracted_text_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_document_version_id"), table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index(op.f("ix_extracted_text_document_version_id"), table_name="extracted_text")
    op.drop_table("extracted_text")

    op.drop_index(op.f("ix_document_versions_uploaded_by_user_id"), table_name="document_versions")
    op.drop_index(op.f("ix_document_versions_status"), table_name="document_versions")
    op.drop_index(op.f("ix_document_versions_sha256_hash"), table_name="document_versions")
    op.drop_index(op.f("ix_document_versions_is_current"), table_name="document_versions")
    op.drop_index(op.f("ix_document_versions_document_id"), table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index(op.f("ix_documents_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_organization_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_created_by_user_id"), table_name="documents")
    op.drop_table("documents")

    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_organizations_stripe_subscription_id"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_stripe_customer_id"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_table("organizations")

    risk_scope.drop(op.get_bind(), checkfirst=True)
    clause_type.drop(op.get_bind(), checkfirst=True)
    risk_severity.drop(op.get_bind(), checkfirst=True)
    job_status.drop(op.get_bind(), checkfirst=True)
    document_status.drop(op.get_bind(), checkfirst=True)
    organization_role.drop(op.get_bind(), checkfirst=True)
