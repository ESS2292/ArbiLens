from datetime import UTC, datetime
from io import BytesIO
import logging

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.document import Document
from app.models.report import Report
from app.models.user import User
from app.schemas.reports import ReportGenerateResponse, ReportRead
from app.services.storage import ObjectStorageService
from app.services.summaries import DocumentSummaryService

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, session: Session, storage_service: ObjectStorageService) -> None:
        self.session = session
        self.storage_service = storage_service

    def list_reports(self, *, document_id, current_user: User) -> list[Report]:
        document = self._get_document(document_id, current_user)
        return sorted(document.reports, key=lambda report: report.created_at, reverse=True)

    def generate_report(self, *, document_id, current_user: User) -> ReportGenerateResponse:
        document = self._get_document(document_id, current_user)
        summary = DocumentSummaryService(self.session).get_summary(document_id=document.id, current_user=current_user)
        if summary.generated_from_status != "completed":
            raise AppError(
                "Reports can only be generated for completed analyses.",
                status_code=409,
                code="report_not_ready",
            )

        latest_report = next(
            (
                report
                for report in sorted(document.reports, key=lambda item: item.created_at, reverse=True)
                if report.status == "generated"
            ),
            None,
        )
        if latest_report and latest_report.document_version_id == summary.document_version_id:
            url = self.storage_service.generate_download_url(latest_report.storage_key)
            return ReportGenerateResponse(report=ReportRead.model_validate(latest_report), download_url=url)

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        filename_root = document.filename.rsplit(".", 1)[0] if "." in document.filename else document.filename
        filename = f"{filename_root}-report-{timestamp}.pdf"
        storage_key = f"organizations/{current_user.organization_id}/reports/{document.id}/{filename}"
        report = Report(
            organization_id=current_user.organization_id,
            document_id=document.id,
            document_version_id=summary.document_version_id,
            analysis_job_id=summary.analysis_job_id,
            created_by_user_id=current_user.id,
            storage_key=storage_key,
            filename=filename,
            report_type="pdf",
            status="generating",
        )
        self.session.add(report)
        self.session.flush()

        try:
            pdf_bytes = self._build_pdf(document, current_user, summary)
            self.storage_service.upload_bytes(content=pdf_bytes, key=storage_key, content_type="application/pdf")
            report.status = "generated"
            report.file_size_bytes = len(pdf_bytes)
            report.generated_at = datetime.now(UTC)
            self.session.commit()
        except Exception:
            logger.exception(
                "Report generation failed",
                extra={"document_id": str(document.id), "report_id": str(report.id)},
            )
            report.status = "failed"
            self.session.commit()
            raise

        self.session.refresh(report)
        return ReportGenerateResponse(
            report=ReportRead.model_validate(report),
            download_url=self.storage_service.generate_download_url(report.storage_key),
        )

    def get_report_download(self, *, report_id, current_user: User) -> ReportGenerateResponse:
        report = (
            self.session.query(Report)
            .filter_by(id=report_id, organization_id=current_user.organization_id)
            .one_or_none()
        )
        if report is None:
            raise AppError("Report not found.", status_code=404, code="report_not_found")
        return ReportGenerateResponse(
            report=ReportRead.model_validate(report),
            download_url=self.storage_service.generate_download_url(report.storage_key),
        )

    def _get_document(self, document_id, current_user: User) -> Document:
        document = (
            self.session.query(Document)
            .filter_by(id=document_id, organization_id=current_user.organization_id)
            .one_or_none()
        )
        if document is None:
            raise AppError("Document not found.", status_code=404, code="document_not_found")
        return document

    def _build_pdf(self, document: Document, current_user: User, summary) -> bytes:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 0.75 * inch

        def write_line(text: str, size: int = 10, gap: int = 14) -> None:
            nonlocal y
            if y < 0.8 * inch:
                pdf.showPage()
                y = height - 0.75 * inch
            pdf.setFont("Helvetica", size)
            pdf.drawString(0.75 * inch, y, text[:110])
            y -= gap

        pdf.setTitle(f"ArbiLens Report - {document.filename}")
        write_line("ArbiLens Contract Risk Report", size=16, gap=20)
        write_line(f"Document: {document.filename}")
        write_line(f"Organization: {current_user.organization.name}")
        write_line(f"Overall risk score: {summary.overall_risk_score}")
        write_line(f"Generated at: {summary.updated_at.isoformat() if hasattr(summary.updated_at, 'isoformat') else summary.updated_at}")
        y -= 6
        write_line("Top Risks", size=12, gap=18)
        for issue in summary.top_issues:
            write_line(f"- {issue.title} ({issue.severity}, score {issue.score})")
            write_line(f"  Rationale: {issue.rationale}", gap=12)
            write_line(f"  Recommendation: {issue.recommendation}", gap=12)
            citation = issue.citations[0] if issue.citations else {}
            clause_id = citation.clause_id if hasattr(citation, "clause_id") else citation.get("clause_id", "n/a")
            page_start = citation.page_start if hasattr(citation, "page_start") else citation.get("page_start", "?")
            page_end = citation.page_end if hasattr(citation, "page_end") else citation.get("page_end", "?")
            write_line(
                f"  Citation: clause {clause_id or 'n/a'} pages {page_start}-{page_end}",
                gap=14,
            )

        y -= 6
        write_line("Clause Findings", size=12, gap=18)
        for coverage in summary.clause_coverage_summary:
            write_line(
                f"- {coverage.clause_type.replace('_', ' ').title()}: "
                f"{'present' if coverage.detected else 'missing'} ({coverage.clause_count})"
            )

        y -= 6
        write_line("Negotiation Priorities", size=12, gap=18)
        for priority in summary.negotiation_priorities:
            write_line(f"- {priority.title}: {priority.recommendation}")

        pdf.showPage()
        pdf.save()
        return buffer.getvalue()
