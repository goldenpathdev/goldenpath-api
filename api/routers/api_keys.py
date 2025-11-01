"""API key management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.auth import get_current_user_from_jwt  # Changed from API key to JWT auth
from api.repositories import APIKeyRepository
from api.models import User
from api.schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api/v1/users/me/api-keys", tags=["api-keys"])


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    current_user: User = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db)
):
    """
    List all API keys for the current user.

    Requires: Valid JWT token in Authorization header (dashboard authentication)
    """
    api_key_repo = APIKeyRepository(db)
    keys = await api_key_repo.list_by_user(current_user.user_id)

    return APIKeyListResponse(
        api_keys=[APIKeyResponse.model_validate(key) for key in keys],
        total=len(keys)
    )


@router.post("", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key for the current user.

    The generated API key is only returned once. Save it securely!

    Requires: Valid JWT token in Authorization header (dashboard authentication)
    """
    # Check if email is verified
    if not current_user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Email must be verified before creating API keys"
        )

    api_key_repo = APIKeyRepository(db)

    # Create the key
    api_key, key_record = await api_key_repo.create(
        user_id=current_user.user_id,
        name=request.name,
        scopes=request.scopes
    )

    return APIKeyCreateResponse(
        key_id=key_record.key_id,
        name=key_record.name,
        api_key=api_key,
        key_prefix=key_record.key_prefix,
        scopes=key_record.scopes,
        created_at=key_record.created_at,
        message="Save this API key securely. You won't be able to see it again."
    )


@router.delete("/{key_id}", status_code=204)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an API key.

    Requires: Valid JWT token in Authorization header (dashboard authentication)
    """
    api_key_repo = APIKeyRepository(db)

    # Delete the key (only if it belongs to the current user)
    deleted = await api_key_repo.delete(key_id, current_user.user_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="API key not found or already deleted"
        )

    return None  # 204 No Content
