"""Deterministic risk rubric shared by the API scorer and the evaluator.

The numeric score, severity, and recommendation text are owned here. An LLM may
explain a finding later; it is not allowed to change these fields. The rules
are the same ones the FastAPI scoring service persisted before this extraction.
"""

from collections.abc import Sequence

from app.engine.types import ClauseView, RiskFinding

RISK_CODES: frozenset[str] = frozenset(
    {
        "missing_liability_cap",
        "uncapped_liability",
        "one_sided_indemnity",
        "unilateral_termination",
        "missing_confidentiality",
        "weak_data_protection",
        "unfavorable_dispute_language",
    }
)


def evaluate_risk_flags(clauses: Sequence[ClauseView]) -> list[RiskFinding]:
    """Apply the rubric. The result order matches the historical API scorer."""

    findings: list[RiskFinding] = []
    liability = _select(clauses, "limitation_of_liability")
    if liability is None:
        findings.append(
            _finding(
                category="liability",
                rule_code="missing_liability_cap",
                severity="high",
                score=80,
                title="No limitation of liability clause detected",
                rationale="A liability cap was not found in the extracted clauses.",
                recommendation="Add a mutual limitation of liability clause with explicit caps and exclusions.",
                clause=None,
                clause_index=None,
            )
        )
    elif _uncapped(liability[1].text):
        findings.append(
            _finding(
                category="liability",
                rule_code="uncapped_liability",
                severity="critical",
                score=95,
                title="Potential uncapped liability",
                rationale="The liability language appears to allow uncapped or open-ended exposure.",
                recommendation=(
                    "Cap liability to a negotiated multiple of fees and carve out only limited exceptions."
                ),
                clause=liability[1],
                clause_index=liability[0],
            )
        )

    indemnity = _select(clauses, "indemnification")
    if indemnity is not None and _one_sided(indemnity[1].text):
        findings.append(
            _finding(
                category="indemnity",
                rule_code="one_sided_indemnity",
                severity="high",
                score=78,
                title="One-sided indemnification language",
                rationale="The indemnity clause appears to allocate obligations primarily to one party.",
                recommendation="Make indemnity obligations mutual or narrow triggers to specific breaches.",
                clause=indemnity[1],
                clause_index=indemnity[0],
            )
        )

    termination = _select(clauses, "termination")
    if termination is not None and _unilateral_convenience(termination[1].text):
        findings.append(
            _finding(
                category="termination",
                rule_code="unilateral_termination",
                severity="high",
                score=74,
                title="Unilateral termination for convenience",
                rationale="Termination language appears to favor only one side.",
                recommendation="Require mutual termination rights or add notice and cure protections.",
                clause=termination[1],
                clause_index=termination[0],
            )
        )

    confidentiality = _select(clauses, "confidentiality")
    if confidentiality is None:
        findings.append(
            _finding(
                category="confidentiality",
                rule_code="missing_confidentiality",
                severity="high",
                score=72,
                title="Missing confidentiality protections",
                rationale="No confidentiality clause was detected in the contract text.",
                recommendation="Add confidentiality obligations, permitted disclosures, and survival terms.",
                clause=None,
                clause_index=None,
            )
        )

    data_protection = _select(clauses, "data_protection")
    if data_protection is None or "reasonable security" not in data_protection[1].text.lower():
        findings.append(
            _finding(
                category="data_protection",
                rule_code="weak_data_protection",
                severity="medium",
                score=60,
                title="Weak data protection language",
                rationale=(
                    "The data protection language is missing or does not clearly describe security obligations."
                ),
                recommendation="Add concrete security, incident response, and subprocesser obligations.",
                clause=data_protection[1] if data_protection is not None else None,
                clause_index=data_protection[0] if data_protection is not None else None,
            )
        )

    dispute = _select(clauses, "dispute_resolution")
    if dispute is not None and _unfavorable_forum(dispute[1].text):
        findings.append(
            _finding(
                category="dispute_resolution",
                rule_code="unfavorable_dispute_language",
                severity="medium",
                score=58,
                title="Potentially unfavorable dispute language",
                rationale="The dispute clause appears to impose a venue that may not be balanced.",
                recommendation="Negotiate a neutral forum, venue, or arbitration mechanism.",
                clause=dispute[1],
                clause_index=dispute[0],
            )
        )
    return findings


def _select(clauses: Sequence[ClauseView], clause_type: str) -> tuple[int, ClauseView] | None:
    chosen: tuple[int, ClauseView] | None = None
    for index, clause in enumerate(clauses):
        if clause.clause_type != clause_type:
            continue
        if chosen is None or clause.confidence > chosen[1].confidence:
            chosen = (index, clause)
    return chosen


def _uncapped(text: str) -> bool:
    lowered = text.lower()
    return "unlimited" in lowered or "without limitation" in lowered


def _one_sided(text: str) -> bool:
    lowered = text.lower()
    return "customer shall indemnify" in lowered or "client shall indemnify" in lowered


def _unilateral_convenience(text: str) -> bool:
    lowered = text.lower()
    if "for convenience" not in lowered:
        return False
    return "company may terminate" in lowered or "provider may terminate" in lowered


def _unfavorable_forum(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ("exclusive venue", "vendor's courts", "vendor courts"))


def _finding(
    *,
    category: str,
    rule_code: str,
    severity: str,
    score: int,
    title: str,
    rationale: str,
    recommendation: str,
    clause: ClauseView | None,
    clause_index: int | None,
) -> RiskFinding:
    return RiskFinding(
        category=category,
        rule_code=rule_code,
        severity=severity,
        score=score,
        title=title,
        rationale=rationale,
        recommendation=recommendation,
        clause_index=clause_index,
        char_start=None if clause is None else clause.char_start,
        char_end=None if clause is None else clause.char_end,
    )
