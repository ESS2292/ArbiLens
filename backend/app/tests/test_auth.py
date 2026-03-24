from fastapi.testclient import TestClient

from app.tests.conftest import register_user


def test_register_creates_owner_and_organization(client: TestClient) -> None:
    payload = register_user(client)

    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == "alex@example.com"
    assert payload["user"]["role"] == "owner"
    assert payload["organization"]["name"] == "Acme Legal"


def test_login_returns_access_token(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alex@example.com", "password": "strong-password-123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "alex@example.com"


def test_protected_route_requires_valid_token_and_returns_current_user(client: TestClient) -> None:
    unauthorized = client.get("/api/v1/users/me")
    assert unauthorized.status_code == 401

    registered = register_user(client)
    token = registered["access_token"]

    authorized = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert authorized.status_code == 200
    body = authorized.json()
    assert body["email"] == "alex@example.com"
    assert body["organization"]["name"] == "Acme Legal"


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alex@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_cross_organization_document_access_is_blocked(client: TestClient, db_session) -> None:
    first_user = register_user(client)
    first_token = first_user["access_token"]

    upload = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {first_token}"},
        files={"upload": ("contract.pdf", b"%PDF-1.4 First contract", "application/pdf")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["document_id"]

    second_response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Other Org",
            "full_name": "Other User",
            "email": "other@example.com",
            "password": "another-strong-password-123",
        },
    )
    assert second_response.status_code == 201
    second_token = second_response.json()["access_token"]

    response = client.get(
        f"/api/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"
