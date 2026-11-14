"""Clause-aware and fixed-window chunkers.

Both chunkers emit exact slices: ``document[start:end] == chunk.text``. The
clause-aware chunker cuts on headings so a clause is one span. The fixed-window
chunker is the baseline and ignores those boundaries.
"""

import re

from app.engine.strategy import RetrievalStrategy
from app.engine.types import Chunk

_HEADING_RE = re.compile(r"^(?:Section\s+\d+(?:\.\d+)*[.)]?\s+\S.{0,80}|\d+(?:\.\d+)*[.)]\s+[A-Z][^\n]{0,80})$")


def is_heading(line: str) -> bool:
    """True when ``line`` looks like a numbered section or article heading."""

    stripped = line.strip()
    if not stripped or len(stripped) > 100 or len(stripped.split()) > 12:
        return False
    return _HEADING_RE.match(stripped) is not None


def chunk_document(text: str, strategy: RetrievalStrategy) -> list[Chunk]:
    """Chunk ``text`` with the strategy's mode."""

    if strategy.chunking == "fixed_window":
        return chunk_fixed_window(text, size=strategy.window_size, overlap=strategy.window_overlap)
    return chunk_clause_aware(text, max_chars=strategy.clause_max_chars)


def chunk_fixed_window(text: str, *, size: int, overlap: int) -> list[Chunk]:
    """Slice ``text`` into fixed character windows."""

    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and smaller than size")
    if not text:
        return []
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(_make_chunk(len(chunks), text, start, end, _title_in_slice(text, start, end), "fixed_window"))
        if end >= len(text):
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks


def chunk_clause_aware(text: str, *, max_chars: int) -> list[Chunk]:
    """Split ``text`` on clause headings, then subdivide only inside a clause."""

    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if not text:
        return []
    spans = _clause_spans(text)
    chunks: list[Chunk] = []
    for start, end, title in spans:
        chunks.extend(_split_span(text, start, end, title, max_chars, len(chunks)))
    return chunks


def _clause_spans(text: str) -> list[tuple[int, int, str | None]]:
    headings = _heading_offsets(text)
    if not headings:
        return [(0, len(text), None)]
    spans: list[tuple[int, int, str | None]] = []
    if headings[0][0] > 0:
        spans.append((0, headings[0][0], None))
    for index, (start, title) in enumerate(headings):
        end = headings[index + 1][0] if index + 1 < len(headings) else len(text)
        spans.append((start, end, title))
    return spans


def _heading_offsets(text: str) -> list[tuple[int, str]]:
    offsets: list[tuple[int, str]] = []
    cursor = 0
    for line in text.splitlines(keepends=True):
        if is_heading(line):
            offsets.append((cursor, line.strip()))
        cursor += len(line)
    return offsets


def _split_span(
    text: str,
    start: int,
    end: int,
    title: str | None,
    max_chars: int,
    next_index: int,
) -> list[Chunk]:
    if end - start <= max_chars:
        return [_make_chunk(next_index, text, start, end, title, "clause_aware")]
    chunks: list[Chunk] = []
    cursor = start
    while cursor < end:
        limit = min(end, cursor + max_chars)
        cut = end if limit == end else _preferred_cut(text, cursor, limit)
        if cut <= cursor:
            cut = min(end, cursor + max_chars)
        chunks.append(_make_chunk(next_index + len(chunks), text, cursor, cut, title, "clause_aware"))
        cursor = cut
    return chunks


def _preferred_cut(text: str, start: int, limit: int) -> int:
    window = text[start:limit]
    for separator in ("\n\n", "\n"):
        position = window.rfind(separator)
        if position > 0:
            return start + position + len(separator)
    return limit


def _title_in_slice(text: str, start: int, end: int) -> str | None:
    snippet = text[start:end]
    first_line = snippet.splitlines()[0] if snippet.splitlines() else ""
    if is_heading(first_line):
        return first_line.strip()
    return None


def _make_chunk(
    index: int,
    text: str,
    start: int,
    end: int,
    title: str | None,
    strategy: str,
) -> Chunk:
    return Chunk(
        chunk_id=f"c{index}",
        text=text[start:end],
        char_start=start,
        char_end=end,
        section_title=title,
        strategy=strategy,
    )
