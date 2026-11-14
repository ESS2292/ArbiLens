"""Run baseline and upgraded strategies on a labeled dataset.

The harness always constructs the offline fake providers. ``arbilens eval``
therefore stays deterministic even when ``OPENAI_API_KEY`` is set in the
environment.
"""

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from app.engine.answer import citation_offsets_match
from app.engine.chunking import chunk_document
from app.engine.embeddings import FakeEmbeddingProvider
from app.engine.llm import FakeLLMProvider
from app.engine.pipeline import analyze_document, ask_document
from app.engine.retrieve import retrieve
from app.engine.risks import evaluate_risk_flags
from app.engine.strategy import STRATEGIES, RetrievalStrategy
from app.engine.types import ClauseView, ExtractedClause
from app.evalkit.dataset import Dataset, GoldClause
from app.evalkit.metrics import mean_flag, mean_reciprocal_rank, prf, span_iou, spans_match

IOU_THRESHOLD = 0.5
RECALL_K = 5


@dataclass(frozen=True)
class StrategyScore:
    """Headline metrics for one chunking and retrieval configuration."""

    name: str
    retrieval_recall_at_5: float
    retrieval_mrr: float
    extraction_micro_f1: float
    extraction_type_micro_f1: float
    citation_faithfulness: float
    offset_integrity: float
    risk_flag_accuracy: float
    risk_flag_micro_f1: float
    per_type_f1: dict[str, float]


@dataclass(frozen=True)
class EvalReport:
    """Comparison of the named strategies on one dataset."""

    provider: str
    dataset_fingerprint: str
    contract_count: int
    question_count: int
    strategies: dict[str, StrategyScore]


def run_evaluation(dataset: Dataset, strategies: Sequence[RetrievalStrategy] | None = None) -> EvalReport:
    """Score each strategy. Providers are the deterministic offline fakes."""

    chosen = list(strategies) if strategies is not None else [STRATEGIES["baseline"], STRATEGIES["upgraded"]]
    embedder = FakeEmbeddingProvider()
    reader = FakeLLMProvider()
    scores = {
        strategy.name: _score_strategy(dataset, strategy, embedder=embedder, reader=reader) for strategy in chosen
    }
    return EvalReport(
        provider=embedder.name,
        dataset_fingerprint=fingerprint_dataset(dataset),
        contract_count=len(dataset.contracts),
        question_count=dataset.question_count,
        strategies=scores,
    )


def fingerprint_dataset(dataset: Dataset) -> str:
    """Short hash of the label file and contract bytes, for the written report."""

    hasher = hashlib.sha256()
    hasher.update(dataset.labels_path.read_bytes())
    for contract in dataset.contracts:
        hasher.update(contract.contract_id.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(contract.text.encode("utf-8"))
    return hasher.hexdigest()[:16]


def _score_strategy(
    dataset: Dataset,
    strategy: RetrievalStrategy,
    *,
    embedder: FakeEmbeddingProvider,
    reader: FakeLLMProvider,
) -> StrategyScore:
    recall_hits: list[bool] = []
    ranks: list[int | None] = []
    faithful: list[bool] = []
    integrity: list[bool] = []
    strict_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    loose_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    risk_exact = 0
    risk_tp = risk_fp = risk_fn = 0

    for contract in dataset.contracts:
        analysis = analyze_document(contract.text, strategy)
        _accumulate_extraction(strict_counts, contract.clauses, analysis.clauses, minimum_iou=IOU_THRESHOLD)
        _accumulate_extraction(loose_counts, contract.clauses, analysis.clauses, minimum_iou=0.0)
        predicted_risks = {finding.rule_code for finding in analysis.risks}
        gold_risks = set(contract.risks)
        if predicted_risks == gold_risks:
            risk_exact += 1
        risk_tp += len(predicted_risks & gold_risks)
        risk_fp += len(predicted_risks - gold_risks)
        risk_fn += len(gold_risks - predicted_risks)

        for question in contract.questions:
            answer = ask_document(
                contract.text,
                question.question,
                strategy,
                embedder=embedder,
                llm=reader,
            )
            ranked_texts = _ranked_texts(contract.text, question.question, strategy, embedder)
            rank = _first_relevant_rank(ranked_texts, question.evidence)
            ranks.append(rank)
            recall_hits.append(rank is not None and rank <= RECALL_K)
            offsets_ok = citation_offsets_match(contract.text, answer.citations)
            evidence_cited = any(question.evidence in citation.text for citation in answer.citations)
            faithful.append(offsets_ok and evidence_cited)
            integrity.append(offsets_ok)

    _precision, _recall, strict_f1 = prf(*_micro(strict_counts))
    _type_precision, _type_recall, loose_f1 = prf(*_micro(loose_counts))
    _risk_precision, _risk_recall, risk_f1 = prf(risk_tp, risk_fp, risk_fn)
    per_type = {clause_type: prf(*counts)[2] for clause_type, counts in sorted(strict_counts.items())}
    return StrategyScore(
        name=strategy.name,
        retrieval_recall_at_5=mean_flag(recall_hits),
        retrieval_mrr=mean_reciprocal_rank(ranks),
        extraction_micro_f1=strict_f1,
        extraction_type_micro_f1=loose_f1,
        citation_faithfulness=mean_flag(faithful),
        offset_integrity=mean_flag(integrity),
        risk_flag_accuracy=risk_exact / len(dataset.contracts),
        risk_flag_micro_f1=risk_f1,
        per_type_f1=per_type,
    )


def _ranked_texts(
    text: str,
    question: str,
    strategy: RetrievalStrategy,
    embedder: FakeEmbeddingProvider,
) -> list[str]:
    chunks = chunk_document(text, strategy)
    hits = retrieve(chunks, question, strategy, embedder=embedder)
    return [hit.chunk.text for hit in hits]


def _first_relevant_rank(ranked_texts: Sequence[str], evidence: str) -> int | None:
    for index, chunk_text in enumerate(ranked_texts, start=1):
        if evidence in chunk_text:
            return index
    return None


def _accumulate_extraction(
    counts: dict[str, list[int]],
    gold: Sequence[GoldClause],
    predicted: Sequence[ExtractedClause],
    *,
    minimum_iou: float,
) -> None:
    types = {item.clause_type for item in gold} | {item.clause_type for item in predicted}
    for clause_type in types:
        gold_spans = [item for item in gold if item.clause_type == clause_type]
        pred_spans = [item for item in predicted if item.clause_type == clause_type]
        matched: set[int] = set()
        true_positive = 0
        for prediction in pred_spans:
            partner = _best_unmatched(prediction, gold_spans, matched, minimum_iou=minimum_iou)
            if partner is None:
                continue
            matched.add(partner)
            true_positive += 1
        bucket = counts[clause_type]
        bucket[0] += true_positive
        bucket[1] += len(pred_spans) - true_positive
        bucket[2] += len(gold_spans) - true_positive


def _best_unmatched(
    prediction: ExtractedClause,
    gold_spans: Sequence[GoldClause],
    matched: set[int],
    *,
    minimum_iou: float,
) -> int | None:
    best_index: int | None = None
    best_iou = -1.0
    for index, gold in enumerate(gold_spans):
        if index in matched:
            continue
        if not spans_match(
            prediction.char_start,
            prediction.char_end,
            gold.char_start,
            gold.char_end,
            minimum_iou=minimum_iou,
        ):
            continue
        score = span_iou(prediction.char_start, prediction.char_end, gold.char_start, gold.char_end)
        if best_index is None or score > best_iou:
            best_index = index
            best_iou = score
    return best_index


def _micro(counts: dict[str, list[int]]) -> tuple[int, int, int]:
    true_positive = sum(bucket[0] for bucket in counts.values())
    false_positive = sum(bucket[1] for bucket in counts.values())
    false_negative = sum(bucket[2] for bucket in counts.values())
    return true_positive, false_positive, false_negative


def gold_risk_codes(clauses: Sequence[GoldClause]) -> list[str]:
    """Risk codes the rubric emits for the gold clause text. Used by dataset tests."""

    views = [ClauseView(clause_type=clause.clause_type, text=clause.text, confidence=1.0) for clause in clauses]
    return [finding.rule_code for finding in evaluate_risk_flags(views)]
