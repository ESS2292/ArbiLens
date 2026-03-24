from collections import defaultdict
from difflib import SequenceMatcher

from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import ClauseType
from app.models.user import User
from app.schemas.comparisons import ClauseDiffItem, ComparisonResponse, RiskDiffItem
from app.services.summaries import DocumentSummaryService


class ComparisonService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def compare_documents(self, *, left_document_id, right_document_id, current_user: User) -> ComparisonResponse:
        left = self._get_document(left_document_id, current_user)
        right = self._get_document(right_document_id, current_user)
        left_version = self._latest_version(left)
        right_version = self._latest_version(right)

        left_summary = DocumentSummaryService(self.session).get_summary(document_id=left.id, current_user=current_user)
        right_summary = DocumentSummaryService(self.session).get_summary(document_id=right.id, current_user=current_user)

        clause_differences = self._compare_clauses(left_version, right_version)
        risk_differences, new_risks = self._compare_risks(left_version, right_version)
        protections_removed = [
            diff.clause_type
            for diff in clause_differences
            if diff.left_present and not diff.right_present
        ]
        protections_added = [
            diff.clause_type
            for diff in clause_differences
            if not diff.left_present and diff.right_present
        ]

        return ComparisonResponse(
            left_document_id=str(left.id),
            right_document_id=str(right.id),
            left_filename=left.filename,
            right_filename=right.filename,
            left_overall_score=left_summary.overall_risk_score,
            right_overall_score=right_summary.overall_risk_score,
            score_delta=right_summary.overall_risk_score - left_summary.overall_risk_score,
            clause_differences=clause_differences,
            risk_differences=risk_differences,
            new_risks_introduced=new_risks,
            protections_removed=protections_removed,
            protections_added=protections_added,
        )

    def _get_document(self, document_id, current_user: User) -> Document:
        document = (
            self.session.query(Document)
            .options(
                selectinload(Document.versions).selectinload(DocumentVersion.clauses),
                selectinload(Document.versions).selectinload(DocumentVersion.risks),
            )
            .filter_by(id=document_id, organization_id=current_user.organization_id)
            .one_or_none()
        )
        if document is None:
            raise AppError("Document not found.", status_code=404, code="document_not_found")
        return document

    def _latest_version(self, document: Document) -> DocumentVersion:
        if not document.versions:
            raise AppError(
                "Completed analysis is required before comparison.",
                status_code=409,
                code="comparison_not_ready",
            )
        return max(document.versions, key=lambda version: version.version_number)

    def _compare_clauses(self, left: DocumentVersion, right: DocumentVersion) -> list[ClauseDiffItem]:
        left_by_type = defaultdict(list)
        right_by_type = defaultdict(list)
        for clause in left.clauses:
            left_by_type[clause.clause_type].append(clause)
        for clause in right.clauses:
            right_by_type[clause.clause_type].append(clause)

        diffs: list[ClauseDiffItem] = []
        for clause_type in ClauseType:
            left_clauses = left_by_type.get(clause_type, [])
            right_clauses = right_by_type.get(clause_type, [])
            left_text = "\n".join(sorted(clause.text for clause in left_clauses))
            right_text = "\n".join(sorted(clause.text for clause in right_clauses))
            diffs.append(
                ClauseDiffItem(
                    clause_type=clause_type,
                    left_present=bool(left_clauses),
                    right_present=bool(right_clauses),
                    changed=bool(
                        left_clauses
                        and right_clauses
                        and left_text != right_text
                        and SequenceMatcher(None, left_text, right_text).ratio() < 0.995
                    ),
                    left_clause_ids=[str(clause.id) for clause in left_clauses],
                    right_clause_ids=[str(clause.id) for clause in right_clauses],
                )
            )
        return diffs

    def _compare_risks(self, left: DocumentVersion, right: DocumentVersion) -> tuple[list[RiskDiffItem], list[RiskDiffItem]]:
        left_by_rule = {risk.deterministic_rule_code or risk.title: risk for risk in left.risks}
        right_by_rule = {risk.deterministic_rule_code or risk.title: risk for risk in right.risks}
        keys = sorted(set(left_by_rule) | set(right_by_rule))
        differences: list[RiskDiffItem] = []
        new_risks: list[RiskDiffItem] = []

        for key in keys:
            left_risk = left_by_rule.get(key)
            right_risk = right_by_rule.get(key)
            if left_risk is None and right_risk is not None:
                item = RiskDiffItem(
                    category=right_risk.category,
                    title=right_risk.title,
                    change_type="new_risk",
                    right_score=right_risk.score,
                    right_severity=right_risk.severity,
                    explanation=f"New risk introduced: {right_risk.title}.",
                )
                differences.append(item)
                new_risks.append(item)
            elif left_risk is not None and right_risk is None:
                differences.append(
                    RiskDiffItem(
                        category=left_risk.category,
                        title=left_risk.title,
                        change_type="risk_removed",
                        left_score=left_risk.score,
                        left_severity=left_risk.severity,
                        explanation=f"Risk no longer detected: {left_risk.title}.",
                    )
                )
            elif left_risk and right_risk:
                change_type = "unchanged"
                if right_risk.score > left_risk.score:
                    change_type = "severity_increase"
                elif right_risk.score < left_risk.score:
                    change_type = "severity_decrease"
                elif right_risk.summary != left_risk.summary:
                    change_type = "changed"
                differences.append(
                    RiskDiffItem(
                        category=right_risk.category,
                        title=right_risk.title,
                        change_type=change_type,
                        left_score=left_risk.score,
                        right_score=right_risk.score,
                        left_severity=left_risk.severity,
                        right_severity=right_risk.severity,
                        explanation=self._explain_risk_diff(left_risk.title, change_type),
                    )
                )
        return differences, new_risks

    def _explain_risk_diff(self, title: str, change_type: str) -> str:
        mapping = {
            "severity_increase": f"Severity increased for {title}.",
            "severity_decrease": f"Severity decreased for {title}.",
            "changed": f"Underlying rationale changed for {title}.",
            "unchanged": f"No material change detected for {title}.",
        }
        return mapping.get(change_type, f"Change detected for {title}.")
