"""Value types shared by chunking, retrieval, extraction, and answers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """A slice of a contract. ``text`` is always ``document[char_start:char_end]``."""

    chunk_id: str
    text: str
    char_start: int
    char_end: int
    section_title: str | None
    strategy: str


@dataclass(frozen=True)
class Hit:
    """One retrieved chunk, with optional per-retriever ranks (1-based)."""

    chunk: Chunk
    score: float
    bm25_rank: int | None = None
    embedding_rank: int | None = None
    rerank_score: float | None = None


@dataclass(frozen=True)
class Citation:
    """An exact document span. ``document[char_start:char_end]`` equals ``text``."""

    chunk_id: str
    char_start: int
    char_end: int
    text: str
    section_title: str | None


@dataclass(frozen=True)
class GroundedAnswer:
    """An answer whose quotes were checked against the source document."""

    question: str
    answer: str
    citations: tuple[Citation, ...]
    grounded: bool
    provider: str
    strategy: str


@dataclass(frozen=True)
class ExtractedClause:
    """A clause type assigned to a character span of the source document."""

    clause_type: str
    text: str
    char_start: int
    char_end: int
    confidence: float
    source_method: str
    title: str | None


@dataclass(frozen=True)
class ClauseView:
    """The fields the risk rubric needs. Persistence objects adapt into this."""

    clause_type: str
    text: str
    confidence: float = 1.0
    char_start: int | None = None
    char_end: int | None = None


@dataclass(frozen=True)
class RiskFinding:
    """One deterministic risk flag. ``clause_index`` points into the input list."""

    category: str
    rule_code: str
    severity: str
    score: int
    title: str
    rationale: str
    recommendation: str
    clause_index: int | None
    char_start: int | None = None
    char_end: int | None = None


@dataclass(frozen=True)
class DocumentAnalysis:
    """Chunks, clause tags, and risk flags for one strategy."""

    chunks: tuple[Chunk, ...]
    clauses: tuple[ExtractedClause, ...]
    risks: tuple[RiskFinding, ...]
