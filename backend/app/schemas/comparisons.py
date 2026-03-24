from pydantic import BaseModel


class ClauseDiffItem(BaseModel):
    clause_type: str
    left_present: bool
    right_present: bool
    changed: bool
    left_clause_ids: list[str]
    right_clause_ids: list[str]


class RiskDiffItem(BaseModel):
    category: str
    title: str
    change_type: str
    left_score: int | None = None
    right_score: int | None = None
    left_severity: str | None = None
    right_severity: str | None = None
    explanation: str


class ComparisonResponse(BaseModel):
    left_document_id: str
    right_document_id: str
    left_filename: str
    right_filename: str
    left_overall_score: int
    right_overall_score: int
    score_delta: int
    clause_differences: list[ClauseDiffItem]
    risk_differences: list[RiskDiffItem]
    new_risks_introduced: list[RiskDiffItem]
    protections_removed: list[str]
    protections_added: list[str]
