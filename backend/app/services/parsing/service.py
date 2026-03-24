from app.core.errors import AppError
from app.models.document_version import DocumentVersion
from app.services.parsing.base import ParsedDocument
from app.services.parsing.docx_parser import DocxParsingService
from app.services.parsing.pdf_parser import PdfParsingService


class DocumentParsingService:
    def __init__(self) -> None:
        self.pdf_parser = PdfParsingService()
        self.docx_parser = DocxParsingService()

    def parse(self, document_version: DocumentVersion, content: bytes) -> ParsedDocument:
        if document_version.file_extension == ".pdf":
            return self.pdf_parser.parse(content)
        if document_version.file_extension == ".docx":
            return self.docx_parser.parse(content)
        raise AppError("Unsupported document type for parsing.", status_code=400, code="unsupported_parser")
