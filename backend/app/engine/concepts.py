"""Curated legal concepts used by the offline embedding provider.

This is not a neural model. It is a deterministic stand-in so synonym questions
("monetary exposure" vs "limitation of liability") have a vector signal when no
API key is configured. The phrase list is general contract vocabulary, and the
OpenAI-compatible embedder replaces it entirely when one is configured.
"""

from app.engine.tokenize import tokenize

CONCEPTS: dict[str, tuple[str, ...]] = {
    "liability_cap": (
        "limitation of liability",
        "liability cap",
        "cap on liability",
        "aggregate liability",
        "monetary exposure",
        "liability ceiling",
        "ceiling",
    ),
    "indemnification": (
        "indemnify",
        "indemnification",
        "hold harmless",
        "hold-harmless",
    ),
    "termination": (
        "termination for convenience",
        "may terminate",
        "right to terminate",
    ),
    "auto_renewal": (
        "automatic renewal",
        "auto renewal",
        "renewal term",
        "renews automatically",
    ),
    "confidentiality": (
        "confidentiality",
        "confidential information",
        "non-disclosure",
        "nonpublic secrets",
    ),
    "assignment": (
        "assignment",
        "assign this agreement",
        "may not assign",
    ),
    "payment_terms": (
        "payment terms",
        "invoices are due",
        "payment due",
    ),
    "dispute_resolution": (
        "dispute resolution",
        "arbitration",
        "exclusive venue",
        "exclusive jurisdiction",
    ),
    "governing_law": (
        "governing law",
        "choice of law",
    ),
    "ip_ownership": (
        "intellectual property",
        "work product",
        "ip ownership",
    ),
    "data_protection": (
        "data protection",
        "personal data",
        "reasonable security",
        "security measures",
    ),
    "warranty": (
        "disclaimer of warranties",
        "as is",
        "warranty",
    ),
    "force_majeure": (
        "force majeure",
        "acts of god",
    ),
    "sla": (
        "service level",
        "uptime",
        "availability commitment",
    ),
    "audit": (
        "audit rights",
        "inspection rights",
        "books and records",
    ),
}

CONCEPT_NAMES: tuple[str, ...] = tuple(CONCEPTS)


def active_concepts(text: str) -> set[str]:
    """Return concept ids whose phrases occur in ``text``."""

    lowered = text.lower()
    return {name for name, phrases in CONCEPTS.items() if any(phrase in lowered for phrase in phrases)}


def concept_overlap(query: str, text: str) -> float:
    """Fraction of the query's concepts that also fire on ``text``."""

    wanted = active_concepts(query)
    if not wanted:
        return 0.0
    return len(wanted & active_concepts(text)) / len(wanted)


def token_overlap(query: str, text: str) -> float:
    """Fraction of query tokens that also appear in ``text``."""

    wanted = set(tokenize(query))
    if not wanted:
        return 0.0
    return len(wanted & set(tokenize(text))) / len(wanted)


def support_score(query: str, text: str) -> float:
    """Blend concept overlap and token overlap into a 0..1 support score."""

    return (0.65 * concept_overlap(query, text)) + (0.35 * token_overlap(query, text))
