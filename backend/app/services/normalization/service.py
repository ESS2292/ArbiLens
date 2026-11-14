import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.engine.chunking import chunk_clause_aware
from app.engine.strategy import upgraded_strategy
from app.services.parsing.base import ParsedDocument, ParsedSection

HEADING_PATTERN = re.compile(
    r"^(?:section|article|schedule|appendix|exhibit)?\s*(?:\d+(?:\.\d+)*)[\).\s-]+.+$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ChunkedSection:
    chunk_index: int
    section_title: str | None
    page_start: int | None
    page_end: int | None
    text: str
    token_estimate: int
    char_count: int
    char_start: int
    char_end: int


@dataclass(frozen=True)
class NormalizedDocument:
    cleaned_text: str
    sections: list[ParsedSection]
    chunks: list[ChunkedSection]


class DocumentNormalizationService:
    def normalize(self, parsed_document: ParsedDocument) -> NormalizedDocument:
        global_frequency = self._line_frequency(section.text for section in parsed_document.sections if section.text)
        cleaned_sections = [
            ParsedSection(
                heading=self._normalize_heading(section.heading) if section.heading else None,
                text=self._clean_text(section.text, frequency=global_frequency),
                page_start=section.page_start,
                page_end=section.page_end,
            )
            for section in parsed_document.sections
            if self._clean_text(section.text, frequency=global_frequency)
        ]

        if not cleaned_sections and parsed_document.full_text:
            cleaned_sections = [
                ParsedSection(
                    heading=None,
                    text=self._clean_text(
                        parsed_document.full_text,
                        frequency=self._line_frequency([parsed_document.full_text]),
                    ),
                )
            ]

        cleaned_text, page_ranges = self._assemble(cleaned_sections)

        return NormalizedDocument(
            cleaned_text=cleaned_text,
            sections=cleaned_sections,
            chunks=self._chunk_cleaned_text(cleaned_text, page_ranges),
        )

    def _assemble(self, sections: list[ParsedSection]) -> tuple[str, list[tuple[int, int, int | None, int | None]]]:
        parts: list[str] = []
        ranges: list[tuple[int, int, int | None, int | None]] = []
        cursor = 0
        for index, section in enumerate(sections):
            if index:
                cursor += 2
            piece = f"{section.heading}\n{section.text}" if section.heading else section.text
            start = cursor
            cursor += len(piece)
            parts.append(piece)
            ranges.append((start, cursor, section.page_start, section.page_end))
        raw = "\n\n".join(parts)
        cleaned = raw.strip()
        offset = raw.find(cleaned) if cleaned else 0
        adjusted = [
            (start - offset, end - offset, page_start, page_end)
            for start, end, page_start, page_end in ranges
            if end > offset and start - offset < len(cleaned)
        ]
        return cleaned, adjusted

    def _chunk_cleaned_text(
        self,
        cleaned_text: str,
        page_ranges: list[tuple[int, int, int | None, int | None]],
    ) -> list[ChunkedSection]:
        """Chunk with the same clause-aware splitter the offline engine uses."""

        if not cleaned_text:
            return []
        chunks = chunk_clause_aware(cleaned_text, max_chars=upgraded_strategy().clause_max_chars)
        built: list[ChunkedSection] = []
        for index, chunk in enumerate(chunks):
            page_start, page_end = self._pages_for(chunk.char_start, chunk.char_end, page_ranges)
            built.append(
                self._build_chunk(
                    chunk_index=index,
                    section_title=chunk.section_title,
                    page_start=page_start,
                    page_end=page_end,
                    text=chunk.text,
                    char_start=chunk.char_start,
                )
            )
        return built

    def _pages_for(
        self,
        start: int,
        end: int,
        page_ranges: list[tuple[int, int, int | None, int | None]],
    ) -> tuple[int | None, int | None]:
        overlapping = [
            (page_start, page_end)
            for range_start, range_end, page_start, page_end in page_ranges
            if start < range_end and end > range_start
        ]
        if not overlapping:
            return None, None
        return overlapping[0][0], overlapping[-1][1]

    def _clean_text(self, text: str, *, frequency: dict[str, int]) -> str:
        lines = [line.rstrip() for line in text.splitlines()]
        filtered_lines = self._remove_repeated_noise(lines, frequency=frequency)
        rebuilt: list[str] = []

        for line in filtered_lines:
            stripped = line.strip()
            if not stripped:
                if rebuilt and rebuilt[-1] != "":
                    rebuilt.append("")
                continue
            # Preserve legal numbering while still repairing parser-introduced line wraps.
            if rebuilt and rebuilt[-1].endswith("-") and stripped[:1].islower():
                rebuilt[-1] = f"{rebuilt[-1][:-1]}{stripped.lstrip()}"
                continue
            if rebuilt and self._should_join_lines(rebuilt[-1], stripped):
                rebuilt[-1] = f"{rebuilt[-1].rstrip()} {stripped.lstrip()}"
            else:
                rebuilt.append(stripped)

        normalized = "\n".join(rebuilt)
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _remove_repeated_noise(self, lines: list[str], *, frequency: dict[str, int]) -> list[str]:
        # Repeated short lines are usually headers, footers, or page markers rather than
        # substantive contract text.
        return [line for line in lines if not self._is_repeated_noise(line.strip(), frequency)]

    def _line_frequency(self, texts: Iterable[str]) -> dict[str, int]:
        frequency: dict[str, int] = {}
        for text in texts:
            for line in text.splitlines():
                candidate = line.strip()
                if candidate:
                    frequency[candidate] = frequency.get(candidate, 0) + 1
        return frequency

    def _is_repeated_noise(self, line: str, frequency: dict[str, int]) -> bool:
        if not line:
            return False
        if re.fullmatch(r"page \d+ of \d+", line, re.IGNORECASE):
            return True
        if frequency.get(line, 0) < 2:
            return False
        if len(line) <= 80 and not re.search(r"[.;:]\s*$", line):
            return True
        return False

    def _should_join_lines(self, previous: str, current: str) -> bool:
        if not previous or previous.endswith((".", ";", ":", "?", "!", ")")):
            return False
        if self._looks_like_heading(previous):
            return False
        if self._looks_like_heading(current):
            return False
        if re.match(r"^(?:\d+(?:\.\d+)*|[A-Z]\.)\s+", current):
            return False
        return True

    def _normalize_heading(self, heading: str) -> str:
        heading = re.sub(r"\s+", " ", heading).strip()
        return heading

    def _looks_like_heading(self, line: str) -> bool:
        stripped = line.strip()
        if HEADING_PATTERN.match(stripped):
            return True
        return stripped.isupper() and 3 <= len(stripped) <= 120

    def _build_chunk(
        self,
        *,
        chunk_index: int,
        section_title: str | None,
        page_start: int | None,
        page_end: int | None,
        text: str,
        char_start: int,
    ) -> ChunkedSection:
        char_count = len(text)
        token_estimate = max(1, round(char_count / 4))
        return ChunkedSection(
            chunk_index=chunk_index,
            section_title=section_title,
            page_start=page_start,
            page_end=page_end,
            text=text,
            token_estimate=token_estimate,
            char_count=char_count,
            char_start=char_start,
            char_end=char_start + char_count,
        )
