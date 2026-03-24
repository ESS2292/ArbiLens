from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "arbilens",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    timezone="UTC",
    imports=("app.tasks.document_tasks",),
)
