from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.analysis_job import AnalysisJob
from app.models.enums import DocumentStatus, JobStatus


STATUS_TO_DOCUMENT_STATUS: dict[JobStatus, DocumentStatus] = {
    JobStatus.queued: DocumentStatus.queued,
    JobStatus.parsing: DocumentStatus.parsing,
    JobStatus.parsed: DocumentStatus.parsed,
    JobStatus.analyzing: DocumentStatus.analyzing,
    JobStatus.completed: DocumentStatus.completed,
    JobStatus.failed: DocumentStatus.failed,
}


class AnalysisJobService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def transition(
        self,
        job: AnalysisJob,
        *,
        status: JobStatus,
        stage: str,
        error_code: str | None = None,
        error_message: str | None = None,
        increment_retry: bool = False,
    ) -> None:
        now = datetime.now(UTC)
        job.status = status
        job.current_stage = stage
        job.error_stage = stage if status == JobStatus.failed else None
        job.error_code = error_code if status == JobStatus.failed else None
        job.error_message = error_message if status == JobStatus.failed else None
        job.last_transitioned_at = now
        if increment_retry:
            job.retry_count += 1
        if status == JobStatus.parsing and job.started_at is None:
            job.started_at = now
        if status == JobStatus.completed:
            job.completed_at = now

        document_status = STATUS_TO_DOCUMENT_STATUS[status]
        job.document.status = document_status
        job.document_version.status = document_status

    def clear_artifacts_for_reprocessing(self, job: AnalysisJob) -> None:
        version = job.document_version
        for chunk in list(version.chunks):
            self.session.delete(chunk)
