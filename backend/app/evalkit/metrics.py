"""Span and set metrics for the contract evaluation harness."""

from collections.abc import Sequence


def span_iou(start_a: int, end_a: int, start_b: int, end_b: int) -> float:
    """Intersection over union for two half-open character spans."""

    intersection = max(0, min(end_a, end_b) - max(start_a, start_b))
    union = max(end_a, end_b) - min(start_a, start_b)
    if union <= 0:
        return 0.0
    return intersection / union


def spans_match(
    start_a: int,
    end_a: int,
    start_b: int,
    end_b: int,
    *,
    minimum_iou: float,
) -> bool:
    """True when the spans overlap and clear ``minimum_iou``.

    ``minimum_iou`` of 0 accepts any positive overlap. A positive threshold
    requires the usual intersection-over-union test.
    """

    intersection = max(0, min(end_a, end_b) - max(start_a, start_b))
    if intersection <= 0:
        return False
    if minimum_iou <= 0:
        return True
    return span_iou(start_a, end_a, start_b, end_b) >= minimum_iou


def prf(true_positive: int, false_positive: int, false_negative: int) -> tuple[float, float, float]:
    """Precision, recall, and F1. Empty counts are a perfect 1.0, not a divide-by-zero."""

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 1.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 1.0
    if precision + recall == 0:
        return precision, recall, 0.0
    f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def mean_reciprocal_rank(ranks: Sequence[int | None]) -> float:
    """Mean of ``1/rank``. A miss is a rank of ``None`` and contributes 0."""

    if not ranks:
        return 0.0
    total = 0.0
    for rank in ranks:
        if rank is not None and rank > 0:
            total += 1.0 / rank
    return total / len(ranks)


def mean_flag(flags: Sequence[bool]) -> float:
    """Fraction of true flags. An empty list is 0, because nothing was measured."""

    if not flags:
        return 0.0
    return sum(1.0 for flag in flags if flag) / len(flags)
