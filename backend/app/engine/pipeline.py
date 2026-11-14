"""Document-level operations used by the CLI and the evaluation harness."""

from collections.abc import Sequence

from app.engine.answer import bind_answer
from app.engine.chunking import chunk_document
from app.engine.embeddings import EmbeddingProvider, default_embedder
from app.engine.extract import extract_clauses
from app.engine.llm import LLMProvider, Passage, default_llm
from app.engine.rerank import Reranker
from app.engine.retrieve import retrieve
from app.engine.risks import evaluate_risk_flags
from app.engine.strategy import RetrievalStrategy
from app.engine.types import Chunk, ClauseView, DocumentAnalysis, GroundedAnswer, Hit


def analyze_document(text: str, strategy: RetrievalStrategy) -> DocumentAnalysis:
    """Chunk, tag clauses, and apply the risk rubric. No model calls."""

    chunks = chunk_document(text, strategy)
    clauses = extract_clauses(chunks)
    views = [
        ClauseView(
            clause_type=clause.clause_type,
            text=clause.text,
            confidence=clause.confidence,
            char_start=clause.char_start,
            char_end=clause.char_end,
        )
        for clause in clauses
    ]
    return DocumentAnalysis(chunks=tuple(chunks), clauses=tuple(clauses), risks=tuple(evaluate_risk_flags(views)))


def ask_document(
    text: str,
    question: str,
    strategy: RetrievalStrategy,
    *,
    embedder: EmbeddingProvider | None = None,
    llm: LLMProvider | None = None,
    reranker: Reranker | None = None,
) -> GroundedAnswer:
    """Chunk, retrieve, and return an answer whose quotes are exact slices."""

    return ask_over_chunks(
        text,
        chunk_document(text, strategy),
        question,
        strategy,
        embedder=embedder,
        llm=llm,
        reranker=reranker,
    )


def ask_over_chunks(
    text: str,
    chunks: Sequence[Chunk],
    question: str,
    strategy: RetrievalStrategy,
    *,
    embedder: EmbeddingProvider | None = None,
    llm: LLMProvider | None = None,
    reranker: Reranker | None = None,
) -> GroundedAnswer:
    """Answer from chunks that were already cut, such as the spans stored at upload."""

    resolved_embedder = embedder if embedder is not None else default_embedder()
    resolved_llm = llm if llm is not None else default_llm()
    hits = retrieve(
        chunks,
        question,
        strategy,
        embedder=resolved_embedder,
        reranker=reranker,
    )
    passages = _passages(hits[: strategy.top_k])
    raw = resolved_llm.answer(question=question, passages=passages)
    return bind_answer(
        text,
        passages,
        raw,
        question=question,
        provider=resolved_llm.name,
        strategy=strategy.name,
    )


def _passages(hits: Sequence[Hit]) -> list[Passage]:
    return [
        Passage(
            chunk_id=hit.chunk.chunk_id,
            char_start=hit.chunk.char_start,
            char_end=hit.chunk.char_end,
            text=hit.chunk.text,
            section_title=hit.chunk.section_title,
        )
        for hit in hits
    ]
