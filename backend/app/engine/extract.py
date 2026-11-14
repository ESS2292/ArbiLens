"""Marker-based clause tagging over already chunked spans.

A chunk that contains a marker is labeled with that clause type, and the span
is the chunk itself. Clause-aware chunks therefore line up with section
boundaries. Fixed windows only cover whatever slice happened to contain the
marker, which is why span F1 moves when the chunker changes.
"""

from collections.abc import Sequence

from app.engine.taxonomy import CLAUSE_MARKERS
from app.engine.types import Chunk, ExtractedClause


def extract_clauses(chunks: Sequence[Chunk]) -> list[ExtractedClause]:
    """Tag each chunk with every marker family it contains."""

    found: list[ExtractedClause] = []
    for chunk in chunks:
        haystack = chunk.text.lower()
        for clause_type, markers in CLAUSE_MARKERS.items():
            if any(marker in haystack for marker in markers):
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
