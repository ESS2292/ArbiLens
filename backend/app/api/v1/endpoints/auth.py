from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    session: Session = Depends(get_db_session),
) -> AuthResponse:
    return AuthService(session).register(payload)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    session: Session = Depends(get_db_session),
) -> AuthResponse:
    return AuthService(session).login(payload)
