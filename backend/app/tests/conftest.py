import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session, get_engine, get_session_factory
from app.main import create_app
from app.models import *  # noqa: F403
from app.services import documents as document_service_module
from app.services.storage import ObjectStorageService, get_object_storage_service
from app.tasks import document_tasks


class FakeObjectStorageService(ObjectStorageService):
    def __init__(self) -> None:
        self.uploaded_objects: dict[str, bytes] = {}
        self.client = self

    def upload_bytes(self, *, content: bytes, key: str, content_type: str) -> str:
        self.uploaded_objects[key] = content
        return key

    def delete_object(self, key: str) -> None:
        self.uploaded_objects.pop(key, None)

    def download_bytes(self, key: str) -> bytes:
        return self.uploaded_objects[key]

    def generate_download_url(self, key: str, expires_in: int = 3600) -> str:
        return f"https://storage.local/{key}?expires_in={expires_in}"

    def head_bucket(self, Bucket: str) -> None:  # noqa: N803
        return None


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    os.environ["MAX_UPLOAD_SIZE_BYTES"] = "1024"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-at-least-32-bytes"
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        get_settings.cache_clear()
        get_engine.cache_clear()
        get_session_factory.cache_clear()


@pytest.fixture()
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    app = create_app()
    storage = FakeObjectStorageService()

    def override_get_db_session() -> Generator[Session, None, None]:
        yield db_session

    def override_storage_service() -> FakeObjectStorageService:
        return storage

    monkeypatch.setattr(document_tasks, "enqueue_document_pipeline", lambda job_id: None)
    monkeypatch.setattr(document_service_module, "enqueue_document_pipeline", lambda job_id: None)
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_object_storage_service] = override_storage_service

    with TestClient(app) as test_client:
        test_client.storage = storage  # type: ignore[attr-defined]
        yield test_client

    app.dependency_overrides.clear()


def register_user(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Acme Legal",
            "full_name": "Alex Founder",
            "email": "alex@example.com",
            "password": "strong-password-123",
        },
    )
    assert response.status_code == 201
    return response.json()
