from fastapi import Depends

from app.api.dependencies.auth import get_current_active_user
from app.core.errors import AppError
from app.models.user import User
from app.services.billing import organization_has_premium_access


def require_premium_access(current_user: User = Depends(get_current_active_user)) -> User:
    if not organization_has_premium_access(current_user.organization):
        raise AppError(
            "An active subscription is required for this feature.",
            status_code=402,
            code="premium_required",
        )
    return current_user
