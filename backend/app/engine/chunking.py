"""Clause-aware and fixed-window chunkers.

Both chunkers emit exact slices: ``document[start:end] == chunk.text``. The
clause-aware chunker cuts on headings so a clause is one span. The fixed-window
chunker is the baseline and ignores those boundaries.
"""

import re

from app.engine.strategy import RetrievalStrategy
from app.engine.types import Chunk

_NUMBERED_RE = re.compile(r"^(?:Section\s+\d+(?:\.\d+)*[.)]?\s+\S.{0,80}|\d+(?:\.\d+)*[.)]\s+[A-Z][^\n]{0,80})$")
_ARTICLE_RE = re.compile(
    r"^(?:article|section)\s+(?:[ivxlcdm]{1,8}|\d+(?:\.\d+)*)(?:[.)]|\s*[—–-])?(?:\s+\S.{0,80})?$",
    re.IGNORECASE,
)
_LETTERED_RE = re.compile(r"^\([a-z]\)\s+[A-Z][A-Za-z0-9'’\-]{0,40}(?:\s+[A-Z][A-Za-z0-9'’\-]{0,40}){0,5}$")
_INLINE_RE = re.compile(r"^(?P<label>[A-Z][A-Za-z0-9'’\-]*(?:\s+[A-Za-z][A-Za-z0-9'’\-]*){0,5}):\s+\S")
_SMALL_WORDS = frozenset({"a", "an", "and", "of", "the", "for", "to", "or", "in", "on"})
_NOT_A_LABEL = frozenset(
    {"the", "a", "an", "if", "each", "this", "that", "no", "not", "notices", "nothing", "either", "neither"}
)
_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


def is_heading(line: str) -> bool:
    """True when ``line`` is only a heading, with no operative sentence on it.

    Inline labels such as ``Payment terms: the buyer pays.`` are section
    breaks but not headings: the sentence splitter still has to read the body.
    """

    return _standalone_title(line) is not None


def section_break_title(line: str) -> str | None:
    """Heading text when ``line`` starts a section, including an inline label."""

    standalone = _standalone_title(line)
    if standalone is not None:
        return standalone
    return _inline_label(line)


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
    previous_blank = True
    for line in text.splitlines(keepends=True):
        title = section_break_title(line) or layout_heading_title(line, previous_line_blank=previous_blank)
        if title is not None:
            offsets.append((cursor, title))
        previous_blank = line.strip() == ""
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
    boundary = _last_sentence_boundary(text, start, limit)
    if boundary is not None:
        return boundary
    return limit


def _last_sentence_boundary(text: str, start: int, limit: int) -> int | None:
    """Last sentence end inside an oversized section, when the line has no break."""

    window = text[start:limit]
    best: int | None = None
    for match in _SENTENCE_END.finditer(window):
        if match.group() == "." and _is_decimal_point(window, match.start()):
            continue
        end = start + match.end()
        if end - start < 40:
            continue
        best = end
        while best < limit and text[best].isspace() and text[best] != "\n":
            best += 1
    return best


def _is_decimal_point(line: str, index: int) -> bool:
    return index > 0 and index + 1 < len(line) and line[index - 1].isdigit() and line[index + 1].isdigit()


def _standalone_title(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or len(stripped) > 100 or len(stripped.split()) > 12:
        return None
    if _NUMBERED_RE.match(stripped) or _ARTICLE_RE.match(stripped) or _LETTERED_RE.match(stripped):
        return stripped
    if _is_all_caps_heading(stripped) or _is_title_case_heading(stripped):
        return stripped
    return None


def layout_heading_title(line: str, *, previous_line_blank: bool) -> str | None:
    """A short unnumbered line after a blank line, with no sentence punctuation.

    ``Ownership of new drawings`` is not title case, but the blank line above it
    is the layout cue that it is a heading rather than a wrapped sentence.
    """

    if not previous_line_blank:
        return None
    stripped = line.strip()
    if not stripped or _standalone_title(stripped) is not None:
        return None
    if any(char in stripped for char in ".!?:;,"):
        return None
    words = stripped.split()
    if not 2 <= len(words) <= 8 or not stripped[0].isupper():
        return None
    return stripped


def _inline_label(line: str) -> str | None:
    stripped = line.strip()
    if len(stripped) > 180:
        return None
    match = _INLINE_RE.match(stripped)
    if match is None:
        return None
    label = match.group("label").strip()
    first = label.split()[0].lower()
    if first in _NOT_A_LABEL or label.endswith("."):
        return None
    return label


def _is_all_caps_heading(line: str) -> bool:
    """A short standalone line whose letters are all capitals."""

    if line.endswith((".", "!", "?")):
        return False
    letters = [char for char in line if char.isalpha()]
    if len(letters) < 3 or len(line.split()) > 8:
        return False
    return all(char.isupper() for char in letters)


def _is_title_case_heading(line: str) -> bool:
    """An unnumbered standalone line in title case, with no sentence punctuation."""

    if any(char in line for char in ".!?:;,"):
        return False
    words = line.split()
    if not 1 <= len(words) <= 8:
        return False
    alphabetic = [word for word in words if any(char.isalpha() for char in word)]
    if not alphabetic:
        return False
    if len(alphabetic) == 1 and len(alphabetic[0]) < 8:
        return False
    for word in alphabetic:
        if word[0].isupper():
            continue
        if word.lower() in _SMALL_WORDS:
            continue
        return False
    return True


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
