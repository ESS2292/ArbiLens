from enum import StrEnum


class OrganizationRole(StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"


class DocumentStatus(StrEnum):
    uploaded = "uploaded"
    queued = "queued"
    parsing = "parsing"
    parsed = "parsed"
    analyzing = "analyzing"
    analyzed = "analyzed"
    completed = "completed"
    failed = "failed"


class JobStatus(StrEnum):
    queued = "queued"
    parsing = "parsing"
    parsed = "parsed"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class RiskSeverity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ClauseType(StrEnum):
    indemnification = "indemnification"
    limitation_of_liability = "limitation_of_liability"
    termination = "termination"
    auto_renewal = "auto_renewal"
    confidentiality = "confidentiality"
    assignment = "assignment"
    payment_terms = "payment_terms"
    dispute_resolution = "dispute_resolution"
    governing_law = "governing_law"
    ip_ownership = "ip_ownership"
    data_protection = "data_protection"
    warranties = "warranties"
    force_majeure = "force_majeure"
    sla = "sla"
    audit_rights = "audit_rights"
    general = "general"


class RiskScope(StrEnum):
    document = "document"
    clause = "clause"
