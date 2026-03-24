from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from app.core.errors import AppError
from app.services.parsing.base import ParsedDocument, ParsedSection


class PdfParsingService:
    parser_name = "pypdf"

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            reader = PdfReader(BytesIO(content))
        except PdfReadError as exc:
            raise AppError("PDF file is corrupted or unreadable.", status_code=400, code="pdf_unreadable") from exc

        if reader.is_encrypted:
            raise AppError("Encrypted PDF files are not supported.", status_code=400, code="pdf_encrypted")

        pages: list[dict[str, object]] = []
        sections: list[ParsedSection] = []
        full_text_parts: list[str] = []

        for page_index, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:
                raise AppError("PDF text extraction failed.", status_code=400, code="pdf_unreadable") from exc
            cleaned = page_text.strip()
            pages.append({"page_number": page_index, "text": cleaned})
            if cleaned:
                full_text_parts.append(cleaned)
                sections.append(
                    ParsedSection(
                        heading=f"Page {page_index}",
                        text=cleaned,
                        page_start=page_index,
                        page_end=page_index,
                    )
                )

        full_text = "\n\n".join(full_text_parts).strip()
        ocr_needed = not bool(full_text)

        if not full_text and not pages:
            raise AppError("PDF file is unreadable.", status_code=400, code="pdf_unreadable")

        return ParsedDocument(
            parser_used=self.parser_name,
            full_text=full_text,
            page_count=len(reader.pages),
            ocr_needed=ocr_needed,
            sections=sections,
            metadata={
                "format": "pdf",
                "pages": pages,
                "ocr_extension_point": "Add OCR fallback for image-only PDFs if required.",
            },
        )
