"""Dataset, metrics, and the regression gate."""

import json
from pathlib import Path

import pytest

from app.engine.chunking import chunk_fixed_window
from app.engine.strategy import BASELINE_WINDOW_CHARS
from app.engine.tokenize import tokenize
from app.evalkit.dataset import load_dataset
from app.evalkit.metrics import mean_reciprocal_rank, prf, span_iou, spans_match
from app.evalkit.paths import find_repo_root
from app.evalkit.report import render_headline_table, report_to_json
from app.evalkit.runner import gold_risk_codes, run_evaluation
from app.evalkit.thresholds import load_thresholds, threshold_failures

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


def test_upgraded_strategy_beats_baseline_and_clears_the_gate(tmp_path: Path) -> None:
    report = run_evaluation(load_dataset(LABELS))
    baseline = report.strategies["baseline"]
    upgraded = report.strategies["upgraded"]
    assert report.provider == "fake"
    assert upgraded.retrieval_recall_at_5 > baseline.retrieval_recall_at_5
    assert upgraded.extraction_micro_f1 > baseline.extraction_micro_f1
    assert upgraded.citation_faithfulness > baseline.citation_faithfulness
    assert upgraded.offset_integrity == 1
    assert baseline.extraction_type_micro_f1 > baseline.extraction_micro_f1
    failures = threshold_failures(report, load_thresholds(THRESHOLDS))
    assert failures == []
    table = render_headline_table(report)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert table in readme
    committed = json.loads((ROOT / "eval" / "reports" / "latest.json").read_text(encoding="utf-8"))
    assert committed == json.loads(report_to_json(report))
    broken = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    broken["upgraded"]["retrieval_recall_at_5"] = 1.1
    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    assert threshold_failures(report, load_thresholds(path))


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
