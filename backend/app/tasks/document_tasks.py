import logging
from http import HTTPStatus
from uuid import UUID

from celery import Task, chain
from celery.exceptions import Retry
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.db.session import get_session_factory
from app.models.analysis_job import AnalysisJob
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.extracted_text import ExtractedText
from app.models.enums import JobStatus
from app.services.extraction import ClauseExtractionService
from app.services.jobs import AnalysisJobService
from app.services.normalization.service import DocumentNormalizationService
from app.services.parsing.base import ParsedDocument, ParsedSection
from app.services.parsing.service import DocumentParsingService
from app.services.scoring import DeterministicRiskScoringService
from app.services.storage import get_object_storage_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_job(session: Session, job_id: str) -> AnalysisJob:
    job = session.scalar(
        select(AnalysisJob)
        .options(
            selectinload(AnalysisJob.document),
            selectinload(AnalysisJob.document_version).selectinload(DocumentVersion.extracted_text),
            selectinload(AnalysisJob.document_version).selectinload(DocumentVersion.chunks),
        )
        .where(AnalysisJob.id == UUID(job_id))
    )
    if job is None:
        raise AppError("Analysis job not found.", status_code=404, code="job_not_found")
    return job


def _sanitize_task_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, AppError):
        return exc.code, exc.message
    return "pipeline_error", "Document processing failed."


def _maybe_retry(task: Task, exc: Exception, stage: str) -> None:
    # Only retry failures that are plausibly transient. Validation and contract-shape
    # errors should fail the job deterministically instead of looping in the queue.
    if isinstance(exc, AppError) and exc.code not in {"storage_read_error", "storage_error"}:
        return
    if task.request.retries >= task.max_retries:
        return
    logger.warning(
        "Retrying pipeline task",
        extra={
            "stage": stage,
            "retry": task.request.retries + 1,
        },
    )
    raise task.retry(exc=exc, countdown=min(60, 2 ** (task.request.retries + 1)))


def enqueue_document_pipeline(job_id: str) -> None:
    chain(
        parse_document_task.s(job_id),
        normalize_document_task.s(),
        extract_clauses_task.s(),
        analyze_risks_task.s(),
    ).apply_async()


def _parsed_document_from_extracted_text(extracted_text: ExtractedText) -> ParsedDocument:
    representation = extracted_text.structured_representation or {}
    sections_data = representation.get("sections", [])
    sections = [
        ParsedSection(
            heading=section.get("heading"),
            text=section.get("text", ""),
            page_start=section.get("page_start"),
            page_end=section.get("page_end"),
        )
        for section in sections_data
        if section.get("text")
    ]
    metadata = representation.get("metadata", {})
    return ParsedDocument(
        parser_used=extracted_text.parser_used,
        full_text=extracted_text.full_text,
        page_count=extracted_text.page_count,
        ocr_needed=extracted_text.ocr_needed,
        sections=sections,
        metadata=metadata if isinstance(metadata, dict) else {},
    )


@celery_app.task(name="document_pipeline.parse_document_task", bind=True, max_retries=3)
def parse_document_task(self, job_id: str) -> str:
    session: Session = get_session_factory()()
    try:
        job = _get_job(session, job_id)
        if job.status == JobStatus.completed:
            return job_id
        # Parsing can be re-entered after worker retries or partial pipeline recovery.
        # If extracted text already exists and the job has moved past parsing, keep the
        # pipeline idempotent by short-circuiting instead of duplicating artifacts.
        if job.document_version.extracted_text is not None and job.current_stage in {
            "parsed",
            "normalizing",
            "normalized",
            "extracting_clauses",
            "analyzing_risks",
            "completed",
        }:
            return job_id
        job_service = AnalysisJobService(session)
        job_service.transition(
            job,
            status=JobStatus.parsing,
            stage="parsing",
            increment_retry=self.request.retries > 0,
        )
        session.commit()

        storage_service = get_object_storage_service()
        content = storage_service.download_bytes(job.document_version.storage_key)
        parsed_document = DocumentParsingService().parse(job.document_version, content)

        if job.document_version.extracted_text is not None:
            session.delete(job.document_version.extracted_text)
            session.flush()

        extracted_text = ExtractedText(
            document_version_id=job.document_version.id,
            full_text=parsed_document.full_text,
            parser_used=parsed_document.parser_used,
            page_count=parsed_document.page_count,
            ocr_needed=parsed_document.ocr_needed,
            structured_representation=parsed_document.as_structured_representation(),
            extractor_name=parsed_document.parser_used,
        )
        session.add(extracted_text)
        job_service.transition(job, status=JobStatus.parsed, stage="parsed")
        session.commit()
        return job_id
    except Retry:
        raise
    except Exception as exc:
        session.rollback()
        _maybe_retry(self, exc, "parsing")
        if "job" in locals() and job is not None:
            code, message = _sanitize_task_error(exc)
            AnalysisJobService(session).transition(
                job,
                status=JobStatus.failed,
                stage="parsing",
                error_code=code,
                error_message=message,
            )
            session.commit()
        logger.exception("Document parsing task failed", extra={"job_id": job_id})
        raise
    finally:
        session.close()


@celery_app.task(name="document_pipeline.normalize_document_task", bind=True, max_retries=3)
def normalize_document_task(self, job_id: str) -> str:
    session: Session = get_session_factory()()
    try:
        job = _get_job(session, job_id)
        if job.status == JobStatus.completed:
            return job_id
        if job.document_version.extracted_text is None:
            raise AppError(
                "Parsed text is not available for normalization.",
                status_code=HTTPStatus.CONFLICT,
                code="parsed_text_missing",
            )
        if job.document_version.chunks and job.current_stage in {
            "normalized",
            "extracting_clauses",
            "analyzing_risks",
            "completed",
        }:
            return job_id

        job_service = AnalysisJobService(session)
        job_service.transition(
            job,
            status=JobStatus.analyzing,
            stage="normalizing",
            increment_retry=self.request.retries > 0,
        )
        # Re-normalization must replace downstream artifacts in one step so later tasks
        # never see old chunks, clauses, or risks mixed with new ones.
        job_service.clear_artifacts_for_reprocessing(job)
        session.commit()

        parsed_document = _parsed_document_from_extracted_text(job.document_version.extracted_text)
        normalized = DocumentNormalizationService().normalize(parsed_document)
        job.document_version.extracted_text.full_text = normalized.cleaned_text

        for chunk in normalized.chunks:
            session.add(
                DocumentChunk(
                    document_version_id=job.document_version.id,
                    extracted_text_id=job.document_version.extracted_text.id,
                    chunk_index=chunk.chunk_index,
                    section_title=chunk.section_title,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    text=chunk.text,
                    token_count=chunk.token_estimate,
                    char_count=chunk.char_count,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                )
            )

        job.current_stage = "normalized"
        session.commit()
        return job_id
    except Retry:
        raise
    except Exception as exc:
        session.rollback()
        _maybe_retry(self, exc, "normalizing")
        if "job" in locals() and job is not None:
            code, message = _sanitize_task_error(exc)
            AnalysisJobService(session).transition(
                job,
                status=JobStatus.failed,
                stage="normalizing",
                error_code=code,
                error_message=message,
            )
            session.commit()
        logger.exception("Document normalization task failed", extra={"job_id": job_id})
        raise
    finally:
        session.close()


@celery_app.task(name="document_pipeline.extract_clauses_task", bind=True, max_retries=3)
def extract_clauses_task(self, job_id: str) -> str:
    session: Session = get_session_factory()()
    try:
        job = _get_job(session, job_id)
        if job.status == JobStatus.completed:
            return job_id
        if job.document_version.extracted_text is None:
            raise AppError(
                "Parsed text is not available for clause extraction.",
                status_code=HTTPStatus.CONFLICT,
                code="parsed_text_missing",
            )
        if job.document_version.clauses and job.current_stage in {"analyzing_risks", "completed"}:
            return job_id

        AnalysisJobService(session).transition(
            job,
            status=JobStatus.analyzing,
            stage="extracting_clauses",
            increment_retry=self.request.retries > 0,
        )
        session.commit()

        ClauseExtractionService(session=session).extract_and_persist(job.document_version)
        session.commit()
        return job_id
    except Retry:
        raise
    except Exception as exc:
        session.rollback()
        _maybe_retry(self, exc, "extracting_clauses")
        if "job" in locals() and job is not None:
            code, message = _sanitize_task_error(exc)
            AnalysisJobService(session).transition(
                job,
                status=JobStatus.failed,
                stage="extracting_clauses",
                error_code=code,
                error_message=message,
            )
            session.commit()
        logger.exception("Clause extraction task failed", extra={"job_id": job_id})
        raise
    finally:
        session.close()


@celery_app.task(name="document_pipeline.analyze_risks_task", bind=True, max_retries=3)
def analyze_risks_task(self, job_id: str) -> str:
    session: Session = get_session_factory()()
    try:
        job = _get_job(session, job_id)
        if job.status == JobStatus.completed and job.document_version.risks:
            return job_id
        AnalysisJobService(session).transition(
            job,
            status=JobStatus.analyzing,
            stage="analyzing_risks",
            increment_retry=self.request.retries > 0,
        )
        session.commit()

        DeterministicRiskScoringService(session=session).analyze_and_persist(
            document_version=job.document_version,
            analysis_job_id=job.id,
        )
        AnalysisJobService(session).transition(job, status=JobStatus.completed, stage="completed")
        session.commit()
        return job_id
    except Retry:
        raise
    except Exception as exc:
        session.rollback()
        _maybe_retry(self, exc, "analyzing_risks")
        if "job" in locals() and job is not None:
            code, message = _sanitize_task_error(exc)
            AnalysisJobService(session).transition(
                job,
                status=JobStatus.failed,
                stage="analyzing_risks",
                error_code=code,
                error_message=message,
            )
            session.commit()
        logger.exception("Risk analysis task failed", extra={"job_id": job_id})
        raise
    finally:
        session.close()
