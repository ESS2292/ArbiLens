"""Clause markers shared by the API extractor and the offline evaluator.

Keys are ``ClauseType`` values. ``general`` has no markers: it is the fallback
label the database uses when nothing more specific was detected.
"""

CLAUSE_MARKERS: dict[str, tuple[str, ...]] = {
    "indemnification": ("indemn", "hold harmless"),
    "limitation_of_liability": ("limitation of liability", "liability cap", "cap on liability"),
    "termination": ("termination", "terminate"),
    "auto_renewal": ("auto renewal", "automatic renewal", "renewal term"),
    "confidentiality": ("confidentiality", "confidential information", "non-disclosure"),
    "assignment": ("assignment", "assign this agreement"),
    "payment_terms": ("payment terms", "fees", "invoices", "payment due"),
    "dispute_resolution": ("dispute resolution", "arbitration", "venue", "exclusive jurisdiction"),
    "governing_law": ("governing law", "laws of"),
    "ip_ownership": ("intellectual property", "ownership", "work product"),
    "data_protection": ("data protection", "privacy", "personal data", "security measures"),
    "warranties": ("warrant", "as is", "disclaimer"),
    "force_majeure": ("force majeure", "acts of god"),
    "sla": ("service level", "uptime", "availability", "response time"),
    "audit_rights": ("audit", "inspection rights", "books and records"),
}
