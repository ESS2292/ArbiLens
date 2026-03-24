import re
from http import HTTPStatus
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.organization import Organization
from app.models.user import User
from app.models.enums import OrganizationRole
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    OrganizationSummary,
    RegisterRequest,
    UserSummary,
)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def register(self, payload: RegisterRequest) -> AuthResponse:
        try:
            existing_user = self.session.scalar(select(User).where(User.email == payload.email.lower()))
            if existing_user is not None:
                raise AppError(
                    "An account with that email already exists.",
                    status_code=HTTPStatus.CONFLICT,
                    code="email_already_registered",
                )

            organization = Organization(
                name=payload.organization_name,
                slug=self._generate_unique_slug(payload.organization_name),
            )
            user = User(
                organization=organization,
                email=payload.email.lower(),
                full_name=payload.full_name,
                password_hash=hash_password(payload.password),
                role=OrganizationRole.owner,
                is_active=True,
            )
            self.session.add_all([organization, user])
            self.session.commit()
            self.session.refresh(organization)
            self.session.refresh(user)
            return self._build_auth_response(user, organization)
        except Exception:
            self.session.rollback()
            raise

    def login(self, payload: LoginRequest) -> AuthResponse:
        user = self.session.scalar(
            select(User)
            .options(joinedload(User.organization))
            .where(User.email == payload.email.lower())
        )
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AppError(
                "Invalid email or password.",
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_credentials",
            )
        if not user.is_active:
            raise AppError(
                "User account is inactive.",
                status_code=HTTPStatus.FORBIDDEN,
                code="inactive_user",
            )
        return self._build_auth_response(user, user.organization)

    def get_current_user(self, access_token: str) -> User:
        payload = decode_access_token(access_token)
        user_id = payload.get("sub")
        if user_id is None:
            raise AppError(
                "Invalid access token.",
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_token",
            )
        user = self.session.scalar(
            select(User)
            .options(joinedload(User.organization))
            .where(User.id == UUID(user_id))
        )
        if user is None:
            raise AppError(
                "Authenticated user was not found.",
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_token",
            )
        return user

    def _build_auth_response(self, user: User, organization: Organization) -> AuthResponse:
        access_token = create_access_token(str(user.id))
        return AuthResponse(
            access_token=access_token,
            user=UserSummary.model_validate(user),
            organization=OrganizationSummary.model_validate(organization),
        )

    def _generate_unique_slug(self, organization_name: str) -> str:
        base_slug = _slugify(organization_name) or "workspace"
        candidate = base_slug
        suffix = 1
        while self.session.scalar(select(Organization).where(Organization.slug == candidate)) is not None:
            suffix += 1
            candidate = f"{base_slug}-{suffix}"
        return candidate
