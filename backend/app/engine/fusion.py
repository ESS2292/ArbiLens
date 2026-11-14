"""Reciprocal rank fusion.

RRF combines ranked lists without requiring the scores to share a scale, which
is what makes BM25 and cosine similarity safe to merge:

    score(d) = sum_i 1 / (k + rank_i(d))

``k`` defaults to 60, the value from Cormack, Clarke, and Buettcher (2009).
A document missing from a list contributes nothing from that list, so a strong
embedding hit is not cancelled by a zero BM25 score.
"""


def reciprocal_rank_fusion(rankings: list[list[str]], *, k: int = 60) -> dict[str, float]:
    """Fuse ranked id lists. Ranks are 1-based positions in each list."""

    if k <= 0:
        raise ValueError("k must be positive")
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))
    return scores
