"""Marker-based clause tagging over already chunked spans.

A chunk that contains a marker is labeled with that clause type, and the span
is the chunk itself. Markers are matched on stemmed tokens, so ``invoice``
meets ``invoices``. A short list of ambiguous single words (``assignment``,
``fees``, ``ownership``, and the like) counts only in the heading. A distractor
sentence that merely says "this assignment" does not receive the assignment tag.
"""

import re
from collections.abc import Sequence

from app.engine.stem import stem_token
from app.engine.taxonomy import CLAUSE_MARKERS, HEADING_ONLY_MARKERS
from app.engine.types import Chunk, ExtractedClause

_TOKEN = re.compile(r"[a-z0-9]+")


def extract_clauses(chunks: Sequence[Chunk]) -> list[ExtractedClause]:
    """Tag each chunk with every marker family it contains."""

    found: list[ExtractedClause] = []
    for chunk in chunks:
        body_stems = _stems(chunk.text)
        title_stems = _stems(chunk.section_title or "")
        for clause_type, markers in CLAUSE_MARKERS.items():
            if any(_marker_hits(marker, title_stems, body_stems) for marker in markers):
                found.append(
                    ExtractedClause(
                        clause_type=clause_type,
                        text=chunk.text,
                        char_start=chunk.char_start,
                        char_end=chunk.char_end,
                        confidence=0.82,
                        source_method="heuristic",
                        title=chunk.section_title,
                    )
                )
    return found


def _marker_hits(marker: str, title_stems: list[str], body_stems: list[str]) -> bool:
    needle = _stems(marker)
    if not needle:
        return False
    if len(needle) == 1 and needle[0] in HEADING_ONLY_MARKERS:
        return _contains(title_stems, needle)
    return _contains(title_stems, needle) or _contains(body_stems, needle)


def _contains(haystack: list[str], needle: list[str]) -> bool:
    if len(needle) > len(haystack):
        return False
    width = len(needle)
    for index in range(len(haystack) - width + 1):
        if all(_same_stem(needle[offset], haystack[index + offset]) for offset in range(width)):
            return True
    return False


def _same_stem(marker: str, token: str) -> bool:
    if marker == token:
        return True
    return len(marker) >= 6 and token.startswith(marker)


def _stems(text: str) -> list[str]:
    return [stem_token(token) for token in _TOKEN.findall(text.lower())]
