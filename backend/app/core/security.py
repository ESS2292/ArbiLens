from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.errors import AppError

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_context.verify(plain_password, password_hash)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire_at,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as exc:
        raise AppError("Invalid or expired access token.", status_code=401, code="invalid_token") from exc

    if payload.get("type") != "access":
        raise AppError("Invalid access token type.", status_code=401, code="invalid_token")
    return payload
