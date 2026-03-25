import logging
import hashlib
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.analysis_job import AnalysisJob
from app.models.risk import Risk
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import DocumentStatus, JobStatus
from app.models.user import User
from app.schemas.documents import DocumentListItem, DocumentStatusResponse, DocumentUploadResponse
from app.services.storage import ObjectStorageService
from app.tasks.document_tasks import enqueue_document_pipeline

logger = logging.getLogger(__name__)

ALLOWED_UPLOADS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocumentService:
    def __init__(
        self,
        session: Session,
        storage_service: ObjectStorageService | None = None,
    ) -> None:
        self.session = session
        self.storage_service = storage_service
        self.settings = get_settings()

    def list_documents_for_organization(self, organization_id: str) -> list[DocumentListItem]:
        documents = self.session.scalars(
            select(Document)
            .options(selectinload(Document.versions).selectinload(DocumentVersion.risks))
            .where(Document.organization_id == organization_id)
            .order_by(Document.created_at.desc())
        )
        return [
            DocumentListItem(
                id=document.id,
                filename=document.filename,
                status=document.status,
                latest_version_number=document.latest_version_number,
                created_at=document.created_at,
                updated_at=document.updated_at,
                overall_risk_score=self._overall_risk_score(
                    max(document.versions, key=lambda version: version.version_number).risks
                    if document.versions
                    else []
                ),
            )
            for document in documents
        ]

    def get_document_status(self, *, document_id: UUID, current_user: User) -> DocumentStatusResponse:
        document = self.session.scalar(
            select(Document)
            .options(
                selectinload(Document.versions),
                selectinload(Document.analysis_jobs),
            )
            .where(
                Document.id == document_id,
                Document.organization_id == current_user.organization_id,
            )
        )
        if document is None:
            raise AppError("Document not found.", status_code=404, code="document_not_found")
        if not document.versions or not document.analysis_jobs:
            raise AppError(
                "Document processing state is incomplete.",
                status_code=409,
                code="document_state_incomplete",
            )

        latest_version = max(document.versions, key=lambda version: version.version_number)
        latest_job = max(document.analysis_jobs, key=lambda job: job.created_at)
        return DocumentStatusResponse(
            document_id=document.id,
            document_version_id=latest_version.id,
            document_status=document.status,
            job_id=latest_job.id,
            job_status=latest_job.status,
            current_stage=latest_job.current_stage,
            error_stage=latest_job.error_stage,
            error_code=latest_job.error_code,
            updated_at=latest_job.last_transitioned_at,
        )

    def _overall_risk_score(self, risks: list[Risk]) -> int | None:
        if not risks:
            return None
        return min(100, round(sum(risk.score for risk in risks) / len(risks)))

    async def upload_document(
        self,
        *,
        upload: UploadFile,
        current_user: User,
    ) -> DocumentUploadResponse:
        storage_key: str | None = None
        should_cleanup_storage = True
        try:
            filename = Path(upload.filename or "").name
            if not filename:
                raise AppError(
                    "Uploaded file name is invalid.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    code="invalid_filename",
                )
            suffix = Path(filename).suffix.lower()
            expected_content_type = ALLOWED_UPLOADS.get(suffix)
            if expected_content_type is None:
                raise AppError(
                    "Only PDF and DOCX files are supported.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    code="unsupported_file_extension",
                )
            if upload.content_type != expected_content_type:
                raise AppError(
                    "Uploaded file MIME type does not match the allowed file types.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    code="unsupported_file_type",
                )

            content = await upload.read()
            if not content:
                raise AppError(
                    "Uploaded file is empty.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    code="empty_file",
                )
            if len(content) > self.settings.max_upload_size_bytes:
                raise AppError(
                    "Uploaded file exceeds the configured maximum size.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    code="file_too_large",
                )
            self._validate_file_content(filename=filename, suffix=suffix, content=content)

            sha256_hash = hashlib.sha256(content).hexdigest()

            next_document = Document(
                organization_id=current_user.organization_id,
                created_by_user_id=current_user.id,
                filename=filename,
                status=DocumentStatus.queued,
                latest_version_number=1,
            )
            self.session.add(next_document)
            self.session.flush()

            storage_key = (
                f"organizations/{current_user.organization_id}/documents/{next_document.id}/"
                f"versions/1/{filename}"
            )
            if self.storage_service is None:
                raise AppError(
                    "Object storage service is not available.",
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    code="storage_not_configured",
                )
            self.storage_service.upload_bytes(
                content=content,
                key=storage_key,
                content_type=expected_content_type,
            )

            version = DocumentVersion(
                document_id=next_document.id,
                uploaded_by_user_id=current_user.id,
                version_number=1,
                storage_key=storage_key,
                original_filename=filename,
                content_type=expected_content_type,
                file_extension=suffix,
                file_size_bytes=len(content),
                sha256_hash=sha256_hash,
                is_current=True,
                status=DocumentStatus.queued,
            )
            self.session.add(version)
            self.session.flush()

            job = AnalysisJob(
                organization_id=current_user.organization_id,
                document_id=next_document.id,
                document_version_id=version.id,
                requested_by_user_id=current_user.id,
                status=JobStatus.queued,
                current_stage="queued",
            )
            self.session.add(job)
            self.session.commit()
            should_cleanup_storage = False
            self.session.refresh(version)
            self.session.refresh(job)
            try:
                enqueue_document_pipeline(str(job.id))
            except Exception as exc:
                logger.exception("Failed to enqueue document pipeline", extra={"job_id": str(job.id)})
                job.status = JobStatus.failed
                job.current_stage = "queueing"
                job.error_stage = "queueing"
                job.error_code = "queue_error"
                job.error_message = "Background processing could not be started."
                job.document.status = DocumentStatus.failed
                job.document_version.status = DocumentStatus.failed
                self.session.commit()
                raise AppError(
                    "Document upload succeeded, but background processing could not be started.",
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                    code="queue_error",
                ) from exc

            return DocumentUploadResponse(
                document_id=next_document.id,
                document_version_id=version.id,
                job_id=job.id,
                job_status=job.status,
            )
        except Exception:
            self.session.rollback()
            if should_cleanup_storage and storage_key is not None and self.storage_service is not None:
                delete_object = getattr(self.storage_service, "delete_object", None)
                try:
                    if callable(delete_object):
                        delete_object(storage_key)
                except AppError:
                    logger.exception("Failed to clean up uploaded object", extra={"storage_key": storage_key})
            raise

    def _validate_file_content(self, *, filename: str, suffix: str, content: bytes) -> None:
        if suffix == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise AppError(
                    f"{filename} does not contain a valid PDF header.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    code="file_content_mismatch",
                )
            return
        if suffix == ".docx":
            try:
                with ZipFile(BytesIO(content)) as archive:
                    names = set(archive.namelist())
            except BadZipFile as exc:
                raise AppError(
                    f"{filename} is not a valid DOCX file.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    code="file_content_mismatch",
                ) from exc
            required_members = {"[Content_Types].xml", "word/document.xml"}
            if not required_members.issubset(names):
                raise AppError(
                    f"{filename} is missing required DOCX components.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    code="file_content_mismatch",
                )
