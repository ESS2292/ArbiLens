from app.models.user import User
from app.schemas.auth import OrganizationSummary
from app.schemas.users import CurrentUserResponse


class UserService:
    def get_current_user_profile(self, user: User) -> CurrentUserResponse:
        return CurrentUserResponse(
            id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            organization=OrganizationSummary.model_validate(user.organization),
        )
