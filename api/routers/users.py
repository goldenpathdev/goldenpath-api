"""User management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.auth import get_current_user_from_api_key
from api.repositories import UserRepository, APIKeyRepository
from api.models import User
from api.schemas import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserResponse,
    UserUpdateRequest,
    ErrorResponse,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def generate_namespace_from_email(email: str) -> str:
    """Generate a namespace from email (e.g., user@example.com -> @user)."""
    username = email.split("@")[0]
    # Clean up the username
    username = username.replace(".", "").replace("_", "").replace("-", "").lower()
    return f"@{username}"


@router.post("/register", response_model=UserRegisterResponse, status_code=201)
async def register_user(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user (called by Cognito PostAuthentication Lambda).

    This endpoint is typically called automatically after Cognito authentication.
    It creates a user record in the database and optionally generates an API key
    if the email is verified.
    """
    user_repo = UserRepository(db)

    # Check if user already exists
    existing_user = await user_repo.get_by_id(request.user_id)
    if existing_user:
        # User already registered, return existing data
        api_key_repo = APIKeyRepository(db)
        keys = await api_key_repo.list_by_user(existing_user.user_id)

        return UserRegisterResponse(
            user_id=existing_user.user_id,
            email=existing_user.email,
            email_verified=existing_user.email_verified,
            namespace=existing_user.namespace,
            auth_provider=existing_user.auth_provider,
            default_api_key=keys[0].key_prefix if keys else None,
            message="User already registered"
        )

    # Check if email already in use
    existing_email = await user_repo.get_by_email(request.email)
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already in use"
        )

    # Generate namespace
    base_namespace = generate_namespace_from_email(request.email)
    namespace = base_namespace
    counter = 1

    # Ensure namespace is unique
    while await user_repo.get_by_namespace(namespace):
        namespace = f"{base_namespace}{counter}"
        counter += 1

    # Create user
    user = await user_repo.create(
        user_id=request.user_id,
        email=request.email,
        email_verified=request.email_verified,
        name=request.name,
        namespace=namespace,
        auth_provider=request.auth_provider,
    )

    # Generate API key if email is verified
    default_api_key = None
    message = None

    if request.email_verified:
        api_key_repo = APIKeyRepository(db)
        api_key, _ = await api_key_repo.create(
            user_id=user.user_id,
            name="Default API Key",
            scopes=["read", "write"]
        )
        default_api_key = api_key
    else:
        message = "Please verify your email to enable API access"

    return UserRegisterResponse(
        user_id=user.user_id,
        email=user.email,
        email_verified=user.email_verified,
        namespace=user.namespace,
        auth_provider=user.auth_provider,
        default_api_key=default_api_key,
        message=message
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_user_from_api_key)
):
    """
    Get the current authenticated user's profile.

    Requires: Valid API key in Authorization header
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user_from_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current user's profile.

    Requires: Valid API key in Authorization header
    """
    user_repo = UserRepository(db)

    updated_user = await user_repo.update(
        user_id=current_user.user_id,
        name=request.name,
        bio=request.bio,
        github_username=request.github_username
    )

    if not updated_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return updated_user
