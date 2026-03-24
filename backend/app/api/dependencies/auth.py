from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db_session
from app.models.user import User
from app.services.auth import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise AppError("Authentication credentials were not provided.", status_code=401, code="authentication_required")

    return AuthService(session).get_current_user(credentials.credentials)


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise AppError("User account is inactive.", status_code=403, code="inactive_user")
    return current_user
