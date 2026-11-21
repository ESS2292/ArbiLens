"""Named retrieval strategies compared by the evaluation harness."""

from dataclasses import dataclass

# Fixed windows are intentionally shorter than a typical clause and do not
# overlap, so a sentence that crosses a boundary is absent from every window.
BASELINE_WINDOW_CHARS = 320
BASELINE_WINDOW_OVERLAP = 0


@dataclass(frozen=True)
class RetrievalStrategy:
    """How to chunk a contract and which retrievers to fuse."""

    name: str
    chunking: str
    window_size: int = BASELINE_WINDOW_CHARS
    window_overlap: int = BASELINE_WINDOW_OVERLAP
    use_bm25: bool = True
    use_embeddings: bool = False
    use_reranker: bool = False
    rrf_k: int = 60
    retriever_depth: int = 8
    top_k: int = 5
    clause_max_chars: int = 4000
    # "sentence" scores each chunk by its best sentence so a long section is
    # not beaten by a shorter neighbor that shares fewer query words.
    bm25_unit: str = "chunk"
    embedding_rrf_weight: float = 1.0

    def __post_init__(self) -> None:
        if self.chunking not in {"fixed_window", "clause_aware"}:
            raise ValueError(f"unknown chunking mode: {self.chunking}")
        if self.window_size <= 0:
            raise ValueError("window_size must be positive")
        if self.window_overlap < 0 or self.window_overlap >= self.window_size:
            raise ValueError("window_overlap must be >= 0 and smaller than window_size")
        if self.rrf_k <= 0 or self.retriever_depth <= 0 or self.top_k <= 0:
            raise ValueError("rrf_k, retriever_depth, and top_k must be positive")
        if self.clause_max_chars <= 0:
            raise ValueError("clause_max_chars must be positive")
        if self.bm25_unit not in {"chunk", "sentence"}:
            raise ValueError("bm25_unit must be 'chunk' or 'sentence'")
        if self.embedding_rrf_weight < 0:
            raise ValueError("embedding_rrf_weight must be >= 0")


def baseline_strategy() -> RetrievalStrategy:
    """Fixed windows plus BM25. This is the before side of the comparison."""

    return RetrievalStrategy(
        name="baseline",
        chunking="fixed_window",
        window_size=BASELINE_WINDOW_CHARS,
        window_overlap=BASELINE_WINDOW_OVERLAP,
        use_bm25=True,
        use_embeddings=False,
        use_reranker=False,
    )


def upgraded_strategy() -> RetrievalStrategy:
    """Clause spans, BM25 + embeddings fused with RRF, then a lexical reranker."""

    return RetrievalStrategy(
        name="upgraded",
        chunking="clause_aware",
        use_bm25=True,
        use_embeddings=True,
        use_reranker=True,
        bm25_unit="sentence",
        embedding_rrf_weight=0.45,
    )


STRATEGIES: dict[str, RetrievalStrategy] = {
    "baseline": baseline_strategy(),
    "upgraded": upgraded_strategy(),
}
