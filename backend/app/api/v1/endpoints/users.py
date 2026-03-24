from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.users import CurrentUserResponse
from app.services.users import UserService

router = APIRouter()


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: User = Depends(get_current_active_user)) -> CurrentUserResponse:
    return UserService().get_current_user_profile(current_user)
