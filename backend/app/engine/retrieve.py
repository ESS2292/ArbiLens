"""Hybrid retrieval: BM25, embeddings, reciprocal rank fusion, optional rerank."""

from collections.abc import Sequence

from app.engine.bm25 import BM25Index
from app.engine.embeddings import EmbeddingProvider, cosine
from app.engine.fusion import reciprocal_rank_fusion
from app.engine.rerank import LexicalReranker, Reranker
from app.engine.strategy import RetrievalStrategy
from app.engine.types import Chunk, Hit


def retrieve(
    chunks: Sequence[Chunk],
    query: str,
    strategy: RetrievalStrategy,
    *,
    embedder: EmbeddingProvider | None = None,
    reranker: Reranker | None = None,
) -> list[Hit]:
    """Rank ``chunks`` for ``query``. The full ranking is returned, best first."""

    if not chunks or not query.strip():
        return []
    rankings: list[list[str]] = []
    bm25_ranks: dict[str, int] = {}
    embedding_ranks: dict[str, int] = {}

    if strategy.use_bm25:
        ranked = BM25Index(chunks).rank(query)[: strategy.retriever_depth]
        ids = [chunks[index].chunk_id for index, _score in ranked]
        if ids:
            rankings.append(ids)
            bm25_ranks = {chunk_id: rank for rank, chunk_id in enumerate(ids, start=1)}

    if strategy.use_embeddings:
        if embedder is None:
            raise ValueError("strategy uses embeddings but no embedder was provided")
        ids = _embedding_ranking(chunks, query, embedder, strategy.retriever_depth)
        if ids:
            rankings.append(ids)
            embedding_ranks = {chunk_id: rank for rank, chunk_id in enumerate(ids, start=1)}

    fused = reciprocal_rank_fusion(rankings, k=strategy.rrf_k)
    if not fused:
        return []
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    ordered = sorted(fused, key=lambda chunk_id: (-fused[chunk_id], by_id[chunk_id].char_start))
    hits = [
        Hit(
            chunk=by_id[chunk_id],
            score=fused[chunk_id],
            bm25_rank=bm25_ranks.get(chunk_id),
            embedding_rank=embedding_ranks.get(chunk_id),
        )
        for chunk_id in ordered
    ]
    if strategy.use_reranker:
        ranker = reranker if reranker is not None else LexicalReranker()
        hits = ranker.rerank(query, hits)
    return hits


def _embedding_ranking(
    chunks: Sequence[Chunk],
    query: str,
    embedder: EmbeddingProvider,
    depth: int,
) -> list[str]:
    vectors = embedder.embed([query, *[chunk.text for chunk in chunks]])
    if len(vectors) != len(chunks) + 1:
        raise ValueError("embedder returned the wrong number of vectors")
    query_vector = vectors[0]
    scored = [
        (chunk.chunk_id, cosine(query_vector, vectors[index + 1]), chunk.char_start)
        for index, chunk in enumerate(chunks)
    ]
    scored.sort(key=lambda item: (-item[1], item[2]))
    return [chunk_id for chunk_id, _score, _start in scored[:depth]]
