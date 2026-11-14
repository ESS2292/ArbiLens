"""Load the hand-labeled contract set and resolve char offsets from quotes.

Gold spans are stored as the clause text itself, not as hand-counted integers.
The loader finds each quote in the file and fails if it is missing or repeated.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.engine.risks import RISK_CODES
from app.engine.taxonomy import CLAUSE_MARKERS


@dataclass(frozen=True)
class GoldClause:
    clause_type: str
    text: str
    char_start: int
    char_end: int


@dataclass(frozen=True)
class GoldQuestion:
    question_id: str
    question: str
    evidence: str
    claim: str
    kind: str


@dataclass(frozen=True)
class GoldContract:
    contract_id: str
    title: str
    text: str
    source_path: Path
    clauses: tuple[GoldClause, ...]
    risks: tuple[str, ...]
    questions: tuple[GoldQuestion, ...]


@dataclass(frozen=True)
class Dataset:
    labels_path: Path
    contracts: tuple[GoldContract, ...]

    @property
    def question_count(self) -> int:
        return sum(len(contract.questions) for contract in self.contracts)


def load_dataset(labels_path: Path) -> Dataset:
    """Parse ``labels.json`` and the contract files it points at."""

    payload = json.loads(labels_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("contracts"), list):
        raise ValueError(f"{labels_path} must contain a contracts list.")
    contracts: list[GoldContract] = []
    seen_ids: set[str] = set()
    for raw in payload["contracts"]:
        contract = _parse_contract(labels_path.parent, raw)
        if contract.contract_id in seen_ids:
            raise ValueError(f"Duplicate contract id {contract.contract_id}.")
        seen_ids.add(contract.contract_id)
        contracts.append(contract)
    if not contracts:
        raise ValueError("Dataset has no contracts.")
    return Dataset(labels_path=labels_path, contracts=tuple(contracts))


def _parse_contract(data_dir: Path, raw: object) -> GoldContract:
    if not isinstance(raw, dict):
        raise ValueError("Each contract entry must be an object.")
    contract_id = _require_str(raw, "id")
    title = _require_str(raw, "title")
    relative = _require_str(raw, "path")
    source_path = data_dir / relative
    if not source_path.is_file():
        raise ValueError(f"{contract_id} points at missing file {source_path}.")
    text = source_path.read_text(encoding="utf-8")
    clauses = tuple(_parse_clause(contract_id, text, item) for item in _require_list(raw, "clauses"))
    risks = tuple(_require_risk(contract_id, item) for item in _require_list(raw, "risks"))
    questions = tuple(_parse_question(contract_id, text, item) for item in _require_list(raw, "questions"))
    if not questions:
        raise ValueError(f"{contract_id} has no questions.")
    return GoldContract(
        contract_id=contract_id,
        title=title,
        text=text,
        source_path=source_path,
        clauses=clauses,
        risks=risks,
        questions=questions,
    )


def _parse_clause(contract_id: str, text: str, raw: object) -> GoldClause:
    if not isinstance(raw, dict):
        raise ValueError(f"{contract_id} has a clause that is not an object.")
    clause_type = _require_str(raw, "type")
    if clause_type not in CLAUSE_MARKERS:
        raise ValueError(f"{contract_id} has unknown clause type {clause_type}.")
    quote = _require_str(raw, "text")
    start, end = _locate(contract_id, text, quote, kind="clause")
    return GoldClause(clause_type=clause_type, text=quote, char_start=start, char_end=end)


def _parse_question(contract_id: str, text: str, raw: object) -> GoldQuestion:
    if not isinstance(raw, dict):
        raise ValueError(f"{contract_id} has a question that is not an object.")
    question_id = _require_str(raw, "id")
    question = _require_str(raw, "question")
    evidence = _require_str(raw, "evidence")
    claim = _require_str(raw, "claim")
    kind = _require_str(raw, "kind")
    if kind not in {"lexical", "semantic", "straddle", "paraphrase", "distractor"}:
        raise ValueError(f"{question_id} has unknown kind {kind}.")
    _locate(contract_id, text, evidence, kind="evidence")
    if claim in text:
        raise ValueError(f"{question_id} claim is copied from the contract; paraphrase it.")
    return GoldQuestion(
        question_id=question_id,
        question=question,
        evidence=evidence,
        claim=claim,
        kind=kind,
    )


def _locate(contract_id: str, text: str, quote: str, *, kind: str) -> tuple[int, int]:
    start = text.find(quote)
    if start < 0:
        raise ValueError(f"{contract_id} is missing {kind} text: {quote[:80]!r}")
    if text.find(quote, start + 1) != -1:
        raise ValueError(f"{contract_id} repeats {kind} text: {quote[:80]!r}")
    return start, start + len(quote)


def _require_str(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected a non-empty string for {key}.")
    return value


def _require_list(raw: dict[str, object], key: str) -> list[object]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Expected a list for {key}.")
    return value


def _require_risk(contract_id: str, raw: object) -> str:
    if not isinstance(raw, str) or raw not in RISK_CODES:
        raise ValueError(f"{contract_id} has unknown risk code {raw!r}.")
    return raw
