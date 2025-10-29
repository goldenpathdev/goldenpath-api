"""API authentication and authorization."""

from typing import Optional
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.repositories import UserRepository, APIKeyRepository
from api.models import User, APIKey


async def get_current_user_from_api_key(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Authenticate user via API key from Authorization header.

    Expected format: Authorization: Bearer gp_live_xxxxx
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected: Bearer <api_key>"
        )

    api_key = parts[1]

    # Verify API key
    api_key_repo = APIKeyRepository(db)
    key_record = await api_key_repo.verify_key(api_key)

    if not key_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key"
        )

    # Get user
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(key_record.user_id)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


async def get_api_key_from_header(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> APIKey:
    """
    Get the API key record from Authorization header.
    Useful for endpoints that need key metadata.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format"
        )

    api_key = parts[1]

    api_key_repo = APIKeyRepository(db)
    key_record = await api_key_repo.verify_key(api_key)

    if not key_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key"
        )

    return key_record


# Optional: JWT-based auth for dashboard (future implementation)
async def get_current_user_from_jwt(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Authenticate user via Cognito JWT token.
    TODO: Implement JWT verification with Cognito public keys.
    """
    raise HTTPException(
        status_code=501,
        detail="JWT authentication not yet implemented. Use API key for now."
    )


# Legacy functions for Golden Path endpoints (backward compatibility)
async def verify_api_key(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Legacy authentication that returns namespace (for Golden Path endpoints).
    """
    user = await get_current_user_from_api_key(authorization, db)
    return user.namespace


async def optional_verify_api_key(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[str]:
    """
    Optional authentication that returns namespace or None.
    """
    if not authorization:
        return None

    try:
        user = await get_current_user_from_api_key(authorization, db)
        return user.namespace
    except HTTPException:
        return None
