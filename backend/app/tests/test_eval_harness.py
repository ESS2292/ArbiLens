"""Dataset, metrics, and the regression gate."""

import json
from pathlib import Path

import pytest

from app.engine.chunking import chunk_clause_aware, chunk_fixed_window
from app.engine.strategy import BASELINE_WINDOW_CHARS, upgraded_strategy
from app.engine.tokenize import tokenize
from app.evalkit.dataset import load_dataset
from app.evalkit.metrics import mean_reciprocal_rank, prf, span_iou, spans_match
from app.evalkit.paths import find_repo_root
from app.evalkit.report import render_headline_table, suite_to_json
from app.evalkit.runner import gold_risk_codes, run_evaluation
from app.evalkit.thresholds import load_thresholds, suite_failures

ROOT = find_repo_root(Path(__file__))
LABELS = ROOT / "eval" / "data" / "labels.json"
THRESHOLDS = ROOT / "eval" / "thresholds.json"

SEMANTIC_TOKENS = frozenset(
    {
        "ceiling",
        "monetary",
        "exposure",
        "bounds",
        "nonpublic",
        "secrets",
        "treated",
        "carries",
        "harmless",
        "burden",
        "alone",
    }
)


def test_span_metrics_and_empty_prf() -> None:
    assert span_iou(0, 10, 5, 15) == pytest.approx(5 / 15)
    assert span_iou(0, 0, 0, 0) == 0
    assert spans_match(0, 4, 3, 8, minimum_iou=0)
    assert not spans_match(0, 2, 5, 8, minimum_iou=0)
    assert prf(0, 0, 0) == (1.0, 1.0, 1.0)
    assert prf(1, 1, 0)[2] == pytest.approx(2 / 3)
    assert mean_reciprocal_rank([1, None, 2]) == pytest.approx((1 + 0 + 0.5) / 3)
    assert mean_reciprocal_rank([]) == 0


def test_dataset_quotes_are_unique_and_risks_follow_the_rubric() -> None:
    dataset = load_dataset(LABELS)
    assert dataset.question_count == 12
    assert len(dataset.contracts) == 6
    kinds = {question.kind for contract in dataset.contracts for question in contract.questions}
    assert kinds == {"lexical", "semantic", "straddle"}
    for contract in dataset.contracts:
        assert set(gold_risk_codes(contract.clauses)) == set(contract.risks)
        leaked = SEMANTIC_TOKENS & set(tokenize(contract.text))
        assert not leaked
        for question in contract.questions:
            windows = chunk_fixed_window(contract.text, size=BASELINE_WINDOW_CHARS, overlap=0)
            contained = any(question.evidence in window.text for window in windows)
            if question.kind == "straddle":
                assert not contained
            else:
                assert contained


def test_dev_set_beats_baseline_and_heldout_is_not_perfect() -> None:
    dev = run_evaluation(load_dataset(LABELS))
    heldout = run_evaluation(load_dataset(ROOT / "eval" / "data" / "heldout.json"))
    assert dev.strategies["upgraded"].judge == "deterministic"
    assert dev.strategies["upgraded"].retrieval_recall_at_5 > dev.strategies["baseline"].retrieval_recall_at_5
    assert dev.strategies["upgraded"].extraction_micro_f1 > dev.strategies["baseline"].extraction_micro_f1
    assert heldout.strategies["upgraded"].citation_faithfulness < 1
    assert heldout.strategies["upgraded"].extraction_micro_f1 < 1
    reports = {"dev": dev, "heldout": heldout}
    assert suite_failures(reports, load_thresholds(THRESHOLDS)) == []
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "split=dev" in readme
    assert render_headline_table(dev) in readme
    assert render_headline_table(heldout) in readme
    committed = json.loads((ROOT / "eval" / "reports" / "latest.json").read_text(encoding="utf-8"))
    assert committed == json.loads(suite_to_json(reports))


def test_heldout_gold_spans_are_not_the_chunker_output() -> None:
    dataset = load_dataset(ROOT / "eval" / "data" / "heldout.json")
    mismatched = 0
    for contract in dataset.contracts:
        chunks = chunk_clause_aware(contract.text, max_chars=upgraded_strategy().clause_max_chars)
        chunk_texts = {chunk.text for chunk in chunks}
        for clause in contract.clauses:
            if clause.text not in chunk_texts:
                mismatched += 1
    assert mismatched >= 1


def test_dataset_loader_rejects_a_missing_quote(tmp_path: Path) -> None:
    contract = tmp_path / "one.txt"
    contract.write_text("1. Services\nThe supplier performs the work.\n", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "contracts": [
                    {
                        "id": "one",
                        "title": "One",
                        "path": "one.txt",
                        "clauses": [{"type": "confidentiality", "text": "not in the file"}],
                        "risks": [],
                        "questions": [
                            {
                                "id": "q",
                                "question": "What is promised?",
                                "evidence": "The supplier performs the work.",
                                "claim": "The supplier does the work described.",
                                "kind": "lexical",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing clause"):
        load_dataset(labels)
