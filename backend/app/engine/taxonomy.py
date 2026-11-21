"""Clause markers shared by the API extractor and the offline evaluator.

Keys are ``ClauseType`` values. ``general`` has no markers: it is the fallback
label the database uses when nothing more specific was detected.
"""

# These single words also appear in unrelated sentences ("this assignment",
# "legal fees", "the venue of the show"). They tag a chunk only when the
# heading contains them. Multi-word markers in the same family still match
# the body: "assign this agreement" is not heading-only.
HEADING_ONLY_MARKERS = frozenset({"assignment", "ownership", "audit", "fees", "fee", "venue", "privacy"})


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
