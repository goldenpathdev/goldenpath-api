"""User profile management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.auth import get_current_user_from_jwt
from api.repositories import UserRepository, APIKeyRepository
from api.models import User
from api.schemas import UserResponse, UserUpdateRequest, APIKeyListResponse, APIKeyResponse

router = APIRouter(prefix="/api/v1/users/me", tags=["profile"])


@router.get("", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user_from_jwt),
):
    """
    Get the current user's profile information.

    Requires: Valid Cognito JWT token in Authorization header
    """
    return UserResponse.model_validate(current_user)


@router.put("", response_model=UserResponse)
async def update_current_user_profile(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current user's profile information.

    Requires: Valid Cognito JWT token in Authorization header
    """
    user_repo = UserRepository(db)
    updated_user = await user_repo.update(
        user_id=current_user.user_id,
        name=request.name,
        bio=request.bio,
        github_username=request.github_username
    )

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(updated_user)


@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_my_api_keys(
    current_user: User = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db)
):
    """
    List all API keys for the current user.

    This endpoint is for the web dashboard to manage API keys.

    Requires: Valid Cognito JWT token in Authorization header
    """
    api_key_repo = APIKeyRepository(db)
    keys = await api_key_repo.list_by_user(current_user.user_id)

    return APIKeyListResponse(
        api_keys=[APIKeyResponse.model_validate(key) for key in keys],
        total=len(keys)
    )
