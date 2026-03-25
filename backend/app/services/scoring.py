from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session

from app.models.clause import Clause
from app.models.document_version import DocumentVersion
from app.models.enums import ClauseType, RiskScope, RiskSeverity
from app.models.risk import Risk
from app.schemas.ai import RiskExplanationSchema
from app.schemas.references import SourceCitation
from app.services.ai import OpenAIResponsesService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskRuleResult:
    category: str
    rule_code: str
    severity: RiskSeverity
    score: int
    title: str
    rationale: str
    recommendation: str
    clause: Clause | None


class DeterministicRiskScoringService:
    def __init__(self, session: Session, ai_service: OpenAIResponsesService | None = None) -> None:
        self.session = session
        self.ai_service = ai_service or OpenAIResponsesService()

    def analyze_and_persist(self, document_version: DocumentVersion, analysis_job_id: str) -> list[Risk]:
        for risk in list(document_version.risks):
            self.session.delete(risk)
        self.session.flush()

        rule_results = self._evaluate_rules(document_version)
        risks: list[Risk] = []
        for result in rule_results:
            explanation = self._explain_risk(result)
            risks.append(
                Risk(
                    document_id=document_version.document_id,
                    document_version_id=document_version.id,
                    clause_id=result.clause.id if result.clause else None,
                    analysis_job_id=analysis_job_id,
                    scope=RiskScope.clause if result.clause is not None else RiskScope.document,
                    severity=result.severity,
                    category=result.category,
                    title=result.title,
                    summary=explanation.summary,
                    score=result.score,
                    rationale=result.rationale,
                    recommendation=result.recommendation,
                    confidence=explanation.confidence,
                    citations=self._build_citations(document_version=document_version, clause=result.clause),
                    deterministic_rule_code=result.rule_code,
                    evidence_text=result.clause.text if result.clause else None,
                )
            )
        self.session.add_all(risks)
        self.session.flush()
        return risks

    def _evaluate_rules(self, document_version: DocumentVersion) -> list[RiskRuleResult]:
        clauses = list(document_version.clauses)
        results: list[RiskRuleResult] = []

        liability_clause = self._find_clause(clauses, ClauseType.limitation_of_liability)
        if liability_clause is None:
            results.append(
                RiskRuleResult(
                    category="liability",
                    rule_code="missing_liability_cap",
                    severity=RiskSeverity.high,
                    score=80,
                    title="No limitation of liability clause detected",
                    rationale="A liability cap was not found in the extracted clauses.",
                    recommendation="Add a mutual limitation of liability clause with explicit caps and exclusions.",
                    clause=None,
                )
            )
        elif "unlimited" in liability_clause.text.lower() or "without limitation" in liability_clause.text.lower():
            results.append(
                RiskRuleResult(
                    category="liability",
                    rule_code="uncapped_liability",
                    severity=RiskSeverity.critical,
                    score=95,
                    title="Potential uncapped liability",
                    rationale="The liability language appears to allow uncapped or open-ended exposure.",
                    recommendation="Cap liability to a negotiated multiple of fees and carve out only limited exceptions.",
                    clause=liability_clause,
                )
            )

        indemnity_clause = self._find_clause(clauses, ClauseType.indemnification)
        if indemnity_clause and self._is_one_sided(indemnity_clause.text):
            results.append(
                RiskRuleResult(
                    category="indemnity",
                    rule_code="one_sided_indemnity",
                    severity=RiskSeverity.high,
                    score=78,
                    title="One-sided indemnification language",
                    rationale="The indemnity clause appears to allocate obligations primarily to one party.",
                    recommendation="Make indemnity obligations mutual or narrow triggers to specific breaches.",
                    clause=indemnity_clause,
                )
            )

        termination_clause = self._find_clause(clauses, ClauseType.termination)
        if termination_clause and "for convenience" in termination_clause.text.lower() and self._is_unilateral(termination_clause.text):
            results.append(
                RiskRuleResult(
                    category="termination",
                    rule_code="unilateral_termination",
                    severity=RiskSeverity.high,
                    score=74,
                    title="Unilateral termination for convenience",
                    rationale="Termination language appears to favor only one side.",
                    recommendation="Require mutual termination rights or add notice and cure protections.",
                    clause=termination_clause,
                )
            )

        confidentiality_clause = self._find_clause(clauses, ClauseType.confidentiality)
        if confidentiality_clause is None:
            results.append(
                RiskRuleResult(
                    category="confidentiality",
                    rule_code="missing_confidentiality",
                    severity=RiskSeverity.high,
                    score=72,
                    title="Missing confidentiality protections",
                    rationale="No confidentiality clause was detected in the contract text.",
                    recommendation="Add confidentiality obligations, permitted disclosures, and survival terms.",
                    clause=None,
                )
            )

        data_protection_clause = self._find_clause(clauses, ClauseType.data_protection)
        if data_protection_clause is None or "reasonable security" not in data_protection_clause.text.lower():
            results.append(
                RiskRuleResult(
                    category="data_protection",
                    rule_code="weak_data_protection",
                    severity=RiskSeverity.medium,
                    score=60,
                    title="Weak data protection language",
                    rationale="The data protection language is missing or does not clearly describe security obligations.",
                    recommendation="Add concrete security, incident response, and subprocesser obligations.",
                    clause=data_protection_clause,
                )
            )

        dispute_clause = self._find_clause(clauses, ClauseType.dispute_resolution)
        if dispute_clause and any(term in dispute_clause.text.lower() for term in ("exclusive venue", "vendor's courts", "vendor courts")):
            results.append(
                RiskRuleResult(
                    category="dispute_resolution",
                    rule_code="unfavorable_dispute_language",
                    severity=RiskSeverity.medium,
                    score=58,
                    title="Potentially unfavorable dispute language",
                    rationale="The dispute clause appears to impose a venue that may not be balanced.",
                    recommendation="Negotiate a neutral forum, venue, or arbitration mechanism.",
                    clause=dispute_clause,
                )
            )

        return results

    def _explain_risk(self, result: RiskRuleResult) -> RiskExplanationSchema:
        user_prompt = (
            f"Risk category: {result.category}\n"
            f"Rule code: {result.rule_code}\n"
            f"Severity: {result.severity}\n"
            f"Numeric score: {result.score}\n"
            f"Deterministic rationale: {result.rationale}\n"
            f"Recommendation baseline: {result.recommendation}\n"
            f"Clause text excerpt: {(result.clause.text[:1200] if result.clause else 'No clause found')}"
        )
        try:
            response = self.ai_service.generate_structured_output(
                system_prompt=(
                    "You explain a risk that has already been scored deterministically. "
                    "Do not change the score or severity. Provide concise, contract-focused explanation."
                ),
                user_prompt=user_prompt,
                response_schema=RiskExplanationSchema,
                metadata={"task": "risk_explanation", "rule_code": result.rule_code},
            )
            return response
        except Exception:
            logger.warning(
                "Risk explanation generation failed; using deterministic fallback summary",
                extra={"rule_code": result.rule_code},
            )
            return RiskExplanationSchema(
                summary=result.title,
                rationale=result.rationale,
                recommendation=result.recommendation,
                confidence=0.55,
            )

    def _build_citations(
        self,
        *,
        document_version: DocumentVersion,
        clause: Clause | None,
    ) -> list[dict[str, object]]:
        if clause is None:
            # Document-level risks still need a stable citation target so summary and UI
            # layers can remain traceable even when no specific clause was detected.
            first_chunk = min(document_version.chunks, key=lambda chunk: chunk.chunk_index, default=None)
            if first_chunk is not None:
                citation = SourceCitation(
                    document_version_id=str(document_version.id),
                    chunk_id=str(first_chunk.id),
                    page_start=first_chunk.page_start,
                    page_end=first_chunk.page_end,
                    reference_type="document_context",
                )
                return [citation.model_dump()]
            citation = SourceCitation(
                document_version_id=str(document_version.id),
                reference_type="document_context",
            )
            return [citation.model_dump()]
        citation = SourceCitation(
            clause_id=str(clause.id),
            chunk_id=str(clause.chunk_id) if clause.chunk_id else None,
            page_start=clause.page_start,
            page_end=clause.page_end,
            reference_type="clause",
        )
        return [citation.model_dump()]

    def _find_clause(self, clauses: list[Clause], clause_type: ClauseType) -> Clause | None:
        candidates = [clause for clause in clauses if clause.clause_type == clause_type]
        if not candidates:
            return None
        return max(candidates, key=lambda clause: clause.confidence)

    def _is_one_sided(self, text: str) -> bool:
        lowered = text.lower()
        return "customer shall indemnify" in lowered or "client shall indemnify" in lowered

    def _is_unilateral(self, text: str) -> bool:
        lowered = text.lower()
        return "company may terminate" in lowered or "provider may terminate" in lowered
