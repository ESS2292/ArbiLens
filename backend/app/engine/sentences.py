"""Sentence spans that stay aligned with the source string."""

import re

from app.engine.chunking import is_heading


def iter_sentence_spans(text: str) -> list[tuple[int, int, str]]:
    """Yield ``(start, end, sentence)`` with ``text[start:end] == sentence``.

    Heading lines are skipped so a numbered title such as ``1. Payment Terms``
    is not quoted as if it were the operative sentence.
    """

    spans: list[tuple[int, int, str]] = []
    for match in re.finditer(r"[^\n]+", text):
        line = match.group()
        if is_heading(line):
            continue
        spans.extend(_sentences_in_line(line, match.start()))
    return spans


def _sentences_in_line(line: str, line_start: int) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for match in re.finditer(r"[.!?]", line):
        if match.group() == "." and _is_decimal_point(line, match.start()):
            continue
        _append_span(spans, line, line_start, cursor, match.end())
        cursor = match.end()
        while cursor < len(line) and line[cursor].isspace():
            cursor += 1
    if cursor < len(line):
        _append_span(spans, line, line_start, cursor, len(line))
    return spans


def _is_decimal_point(line: str, index: int) -> bool:
    """A period between digits is part of a number, not the end of a sentence."""

    return index > 0 and index + 1 < len(line) and line[index - 1].isdigit() and line[index + 1].isdigit()


def _append_span(
    spans: list[tuple[int, int, str]],
    line: str,
    line_start: int,
    start: int,
    end: int,
) -> None:
    piece = line[start:end]
    stripped = piece.strip()
    if not stripped:
        return
    left = piece.find(stripped)
    absolute = line_start + start + left
    spans.append((absolute, absolute + len(stripped), stripped))
