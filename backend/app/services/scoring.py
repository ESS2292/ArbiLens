import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.engine.risks import evaluate_risk_flags
from app.engine.types import ClauseView
from app.models.clause import Clause
from app.models.document_version import DocumentVersion
from app.models.enums import RiskScope, RiskSeverity
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
        self.ai_service = ai_service

    def analyze_and_persist(self, document_version: DocumentVersion, analysis_job_id: UUID) -> list[Risk]:
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
        views = [
            ClauseView(clause_type=clause.clause_type.value, text=clause.text, confidence=clause.confidence)
            for clause in clauses
        ]
        return [
            RiskRuleResult(
                category=finding.category,
                rule_code=finding.rule_code,
                severity=RiskSeverity(finding.severity),
                score=finding.score,
                title=finding.title,
                rationale=finding.rationale,
                recommendation=finding.recommendation,
                clause=clauses[finding.clause_index] if finding.clause_index is not None else None,
            )
            for finding in evaluate_risk_flags(views)
        ]

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
            response = self._get_ai_service().generate_structured_output(
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

    def _get_ai_service(self) -> OpenAIResponsesService:
        if self.ai_service is None:
            self.ai_service = OpenAIResponsesService()
        return self.ai_service

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
