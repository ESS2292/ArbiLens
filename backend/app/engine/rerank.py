"""Optional rerankers.

The lexical reranker adds a small bonus on top of the fused score. The bonus is
too small to overturn a clear reciprocal-rank lead and large enough to break a
near tie toward the passage that shares the query's concepts.
"""

from collections.abc import Sequence
from typing import Protocol

from app.engine.concepts import support_score
from app.engine.types import Hit

# RRF scores for adjacent ranks differ by about 1/k^2. A bonus under 0.002
# can reorder those neighbors and cannot leapfrog a rank-1-only hit (~0.016).
_RERANK_BONUS = 0.0015


class Reranker(Protocol):
    """Reorders an already retrieved list. It does not search the corpus."""

    name: str

    def rerank(self, query: str, hits: Sequence[Hit]) -> list[Hit]:
        """Return a new list. The input is not mutated."""
        ...


class NullReranker:
    """Identity reranker used when the strategy leaves reranking off."""

    name = "none"

    def rerank(self, query: str, hits: Sequence[Hit]) -> list[Hit]:
        del query
        return list(hits)


class LexicalReranker:
    """Blend the fused score with concept and token support."""

    name = "lexical"

    def rerank(self, query: str, hits: Sequence[Hit]) -> list[Hit]:
        adjusted: list[Hit] = []
        for hit in hits:
            lexical = support_score(query, f"{hit.chunk.section_title or ''}\n{hit.chunk.text}")
            adjusted.append(
                Hit(
                    chunk=hit.chunk,
                    score=hit.score + (_RERANK_BONUS * lexical),
                    bm25_rank=hit.bm25_rank,
                    embedding_rank=hit.embedding_rank,
                    rerank_score=lexical,
                )
            )
        adjusted.sort(key=lambda hit: (-hit.score, hit.chunk.char_start))
        return adjusted
