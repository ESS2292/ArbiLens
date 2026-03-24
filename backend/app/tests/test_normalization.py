from app.services.normalization.service import DocumentNormalizationService
from app.services.parsing.base import ParsedDocument, ParsedSection


def test_normalization_removes_repeated_headers_and_joins_wrapped_lines() -> None:
    parsed = ParsedDocument(
        parser_used="test",
        full_text="",
        page_count=2,
        ocr_needed=False,
        sections=[
            ParsedSection(
                heading="Section 1. Scope",
                text=(
                    "ACME MASTER SERVICES AGREEMENT\n"
                    "Section 1. Scope\n"
                    "This Agreement shall con-\n"
                    "tinue for twelve months.\n"
                    "\n"
                    "Page 1 of 2"
                ),
                page_start=1,
                page_end=1,
            ),
            ParsedSection(
                heading="Section 2. Fees",
                text=(
                    "ACME MASTER SERVICES AGREEMENT\n"
                    "Section 2. Fees\n"
                    "2.1 Fees are due within thirty days.\n"
                    "Page 2 of 2"
                ),
                page_start=2,
                page_end=2,
            ),
        ],
        metadata={},
    )

    result = DocumentNormalizationService().normalize(parsed)

    assert "Page 1 of 2" not in result.cleaned_text
    assert "ACME MASTER SERVICES AGREEMENT" not in result.cleaned_text
    assert "con- tinue" not in result.cleaned_text
    assert "2.1 Fees are due within thirty days." in result.cleaned_text


def test_chunk_generation_and_heading_detection_produce_metadata() -> None:
    parsed = ParsedDocument(
        parser_used="test",
        full_text="",
        page_count=1,
        ocr_needed=False,
        sections=[
            ParsedSection(
                heading=None,
                text="Section 4. Liability\nThe supplier shall maintain insurance.\n\nAdditional obligations apply.",
                page_start=3,
                page_end=4,
            )
        ],
        metadata={},
    )

    result = DocumentNormalizationService().normalize(parsed)

    assert len(result.chunks) >= 1
    first_chunk = result.chunks[0]
    assert first_chunk.section_title == "Section 4. Liability"
    assert first_chunk.page_start == 3
    assert first_chunk.page_end == 4
    assert first_chunk.token_estimate > 0
    assert first_chunk.char_count == len(first_chunk.text)
