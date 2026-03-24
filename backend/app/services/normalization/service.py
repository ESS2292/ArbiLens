import re
from dataclasses import dataclass

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
        cleaned_sections = [
            ParsedSection(
                heading=self._normalize_heading(section.heading) if section.heading else None,
                text=self._clean_text(section.text),
                page_start=section.page_start,
                page_end=section.page_end,
            )
            for section in parsed_document.sections
            if self._clean_text(section.text)
        ]

        if not cleaned_sections and parsed_document.full_text:
            cleaned_sections = [ParsedSection(heading=None, text=self._clean_text(parsed_document.full_text))]

        cleaned_text = "\n\n".join(
            f"{section.heading}\n{section.text}" if section.heading else section.text
            for section in cleaned_sections
        ).strip()

        return NormalizedDocument(
            cleaned_text=cleaned_text,
            sections=cleaned_sections,
            chunks=self._chunk_sections(cleaned_sections),
        )

    def _clean_text(self, text: str) -> str:
        lines = [line.rstrip() for line in text.splitlines()]
        filtered_lines = self._remove_repeated_noise(lines)
        rebuilt: list[str] = []

        for line in filtered_lines:
            stripped = line.strip()
            if not stripped:
                if rebuilt and rebuilt[-1] != "":
                    rebuilt.append("")
                continue
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

    def _remove_repeated_noise(self, lines: list[str]) -> list[str]:
        frequency: dict[str, int] = {}
        for line in lines:
            candidate = line.strip()
            if candidate:
                frequency[candidate] = frequency.get(candidate, 0) + 1

        return [
            line
            for line in lines
            if not self._is_repeated_noise(line.strip(), frequency)
        ]

    def _is_repeated_noise(self, line: str, frequency: dict[str, int]) -> bool:
        if not line:
            return False
        if frequency.get(line, 0) < 2:
            return False
        if re.fullmatch(r"page \d+ of \d+", line, re.IGNORECASE):
            return True
        if len(line) <= 80 and not re.search(r"[.;:]\s*$", line):
            return True
        return False

    def _should_join_lines(self, previous: str, current: str) -> bool:
        if not previous or previous.endswith((".", ";", ":", "?", "!", ")")):
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

    def _chunk_sections(self, sections: list[ParsedSection]) -> list[ChunkedSection]:
        chunks: list[ChunkedSection] = []
        chunk_index = 0
        char_cursor = 0
        max_chars = 1800

        for section in sections:
            title = section.heading or self._detect_heading_from_text(section.text)
            paragraphs = [paragraph.strip() for paragraph in section.text.split("\n\n") if paragraph.strip()]
            current_parts: list[str] = []

            for paragraph in paragraphs or [section.text]:
                proposed = "\n\n".join([*current_parts, paragraph]).strip()
                if current_parts and len(proposed) > max_chars:
                    chunk_text = "\n\n".join(current_parts).strip()
                    chunks.append(
                        self._build_chunk(
                            chunk_index=chunk_index,
                            section_title=title,
                            page_start=section.page_start,
                            page_end=section.page_end,
                            text=chunk_text,
                            char_start=char_cursor,
                        )
                    )
                    char_cursor += len(chunk_text)
                    chunk_index += 1
                    current_parts = [paragraph]
                else:
                    current_parts.append(paragraph)

            if current_parts:
                chunk_text = "\n\n".join(current_parts).strip()
                chunks.append(
                    self._build_chunk(
                        chunk_index=chunk_index,
                        section_title=title,
                        page_start=section.page_start,
                        page_end=section.page_end,
                        text=chunk_text,
                        char_start=char_cursor,
                    )
                )
                char_cursor += len(chunk_text)
                chunk_index += 1

        return chunks

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

    def _detect_heading_from_text(self, text: str) -> str | None:
        first_line = text.splitlines()[0].strip() if text.splitlines() else ""
        return first_line if self._looks_like_heading(first_line) else None
