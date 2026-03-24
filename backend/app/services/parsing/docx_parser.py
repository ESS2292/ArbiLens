from io import BytesIO

from docx import Document as DocxDocument
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.core.errors import AppError
from app.services.parsing.base import ParsedDocument, ParsedSection


class DocxParsingService:
    parser_name = "python-docx"

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            document = DocxDocument(BytesIO(content))
        except Exception as exc:
            raise AppError("DOCX file is corrupted or unreadable.", status_code=400, code="docx_unreadable") from exc

        sections: list[ParsedSection] = []
        current_heading: str | None = None
        current_lines: list[str] = []
        full_text_parts: list[str] = []
        blocks: list[dict[str, object]] = []

        for child in document.element.body.iterchildren():
            if isinstance(child, CT_P):
                paragraph = Paragraph(child, document)
                text = paragraph.text.strip()
                if not text:
                    continue
                style_name = paragraph.style.name if paragraph.style is not None else ""
                is_heading = style_name.lower().startswith("heading")
                blocks.append({"type": "paragraph", "style": style_name, "text": text})
                full_text_parts.append(text)
                if is_heading:
                    if current_lines:
                        sections.append(
                            ParsedSection(heading=current_heading, text="\n".join(current_lines).strip())
                        )
                        current_lines = []
                    current_heading = text
                    continue
                current_lines.append(text)
            elif isinstance(child, CT_Tbl):
                table = Table(child, document)
                rows = [" | ".join(cell.text.strip() for cell in row.cells if cell.text.strip()) for row in table.rows]
                table_text = "\n".join(row for row in rows if row).strip()
                if not table_text:
                    continue
                blocks.append({"type": "table", "text": table_text})
                full_text_parts.append(table_text)
                current_lines.append(table_text)

        if current_lines:
            sections.append(ParsedSection(heading=current_heading, text="\n".join(current_lines).strip()))

        full_text = "\n\n".join(full_text_parts).strip()
        if not full_text:
            raise AppError("DOCX file is unreadable.", status_code=400, code="docx_unreadable")

        return ParsedDocument(
            parser_used=self.parser_name,
            full_text=full_text,
            page_count=None,
            ocr_needed=False,
            sections=sections,
            metadata={
                "format": "docx",
                "blocks": blocks,
                "ocr_extension_point": "OCR fallback can be added for embedded scanned images later.",
            },
        )
