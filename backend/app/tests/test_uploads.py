from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.services.storage import get_object_storage_service
from app.tests.conftest import register_user


def test_upload_success_creates_document_version_and_job(client: TestClient) -> None:
    registered = register_user(client)
    token = registered["access_token"]

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"upload": ("contract.pdf", b"%PDF-1.4 sample contract", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["document_id"]
    assert body["document_version_id"]
    assert body["job_id"]
    assert body["job_status"] == "queued"

    list_response = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["filename"] == "contract.pdf"

    status_response = client.get(
        f"/api/v1/documents/{body['document_id']}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["job_status"] == "queued"


def test_upload_rejects_invalid_extension(client: TestClient) -> None:
    registered = register_user(client)
    token = registered["access_token"]

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"upload": ("contract.txt", b"not supported", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_file_extension"


def test_upload_rejects_invalid_mime_type(client: TestClient) -> None:
    registered = register_user(client)
    token = registered["access_token"]

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"upload": ("contract.pdf", b"%PDF-1.4 sample contract", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_upload_rejects_empty_file(client: TestClient) -> None:
    registered = register_user(client)
    token = registered["access_token"]

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"upload": ("contract.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_file"


def test_upload_rejects_oversized_file(client: TestClient) -> None:
    registered = register_user(client)
    token = registered["access_token"]

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"upload": ("contract.pdf", b"x" * 2048, "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "file_too_large"


def test_upload_rejects_pdf_extension_with_non_pdf_content(client: TestClient) -> None:
    registered = register_user(client)
    token = registered["access_token"]

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"upload": ("contract.pdf", b"not actually a pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "file_content_mismatch"


def test_upload_rejects_docx_extension_with_invalid_archive(client: TestClient) -> None:
    registered = register_user(client)
    token = registered["access_token"]

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "upload": (
                "contract.docx",
                b"PK\x03\x04not-a-real-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "file_content_mismatch"


def test_upload_normalizes_untrusted_filename(client: TestClient) -> None:
    registered = register_user(client)
    token = registered["access_token"]

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"upload": ("../nested/contract.pdf", b"%PDF-1.4 sample contract", "application/pdf")},
    )

    assert response.status_code == 201

    list_response = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["filename"] == "contract.pdf"


def test_upload_returns_clean_error_on_storage_failure(client: TestClient) -> None:
    class _BrokenStorage:
        def upload_bytes(self, *, content: bytes, key: str, content_type: str) -> str:
            raise AppError("Failed to store the uploaded file.", status_code=503, code="storage_error")

    client.app.dependency_overrides[get_object_storage_service] = lambda: _BrokenStorage()
    registered = register_user(client)
    token = registered["access_token"]

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"upload": ("contract.pdf", b"%PDF-1.4 sample contract", "application/pdf")},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "storage_error"
    assert "uploaded file" in response.json()["error"]["message"].lower()
    client.app.dependency_overrides.pop(get_object_storage_service, None)
