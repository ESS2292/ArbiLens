from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedSection:
    heading: str | None
    text: str
    page_start: int | None = None
    page_end: int | None = None


@dataclass(frozen=True)
class ParsedDocument:
    parser_used: str
    full_text: str
    page_count: int | None
    ocr_needed: bool
    sections: list[ParsedSection]
    metadata: dict[str, object]

    def as_structured_representation(self) -> dict[str, object]:
        return {
            "parser_used": self.parser_used,
            "page_count": self.page_count,
            "ocr_needed": self.ocr_needed,
            "metadata": self.metadata,
            "sections": [
                {
                    "heading": section.heading,
                    "text": section.text,
                    "page_start": section.page_start,
                    "page_end": section.page_end,
                }
                for section in self.sections
            ],
        }
