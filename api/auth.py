"""API authentication and authorization."""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.repositories import UserRepository, APIKeyRepository
from api.models import User, APIKey

logger = logging.getLogger(__name__)


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


# JWT-based auth for dashboard
import os
import jwt
import requests
from jose import JWTError
from jose.backends import RSAKey

# Cognito configuration from environment
COGNITO_REGION = os.getenv("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "us-east-1_X9xT6Y23H")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "6fpc4jp30rfl1ojrvmt3r1qbgs")

# Cognito public keys URL
COGNITO_JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"

# Cache for Cognito public keys
_cognito_keys_cache = None

def get_cognito_public_keys():
    """
    Fetch and cache Cognito public keys for JWT verification.
    """
    global _cognito_keys_cache

    if _cognito_keys_cache is not None:
        return _cognito_keys_cache

    try:
        response = requests.get(COGNITO_JWKS_URL, timeout=5)
        response.raise_for_status()
        _cognito_keys_cache = response.json()
        return _cognito_keys_cache
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch Cognito public keys: {str(e)}"
        )


async def get_current_user_from_jwt(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Authenticate user via Cognito JWT token.
    Verifies token signature, expiration, and extracts user info.
    """
    logger.info("JWT authentication started")

    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid Authorization header format: {len(parts)} parts, first part: {parts[0] if parts else 'none'}")
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected: Bearer <jwt_token>"
        )

    token = parts[1]
    logger.info(f"Token received (length: {len(token)}, prefix: {token[:20]}...)")

    try:
        from jose import jwt as jose_jwt

        # Get Cognito public keys
        logger.info("Fetching Cognito public keys")
        keys = get_cognito_public_keys()
        logger.info(f"Retrieved {len(keys.get('keys', []))} public keys from Cognito")

        # Decode header to get key ID
        logger.info("Decoding JWT header")
        headers = jose_jwt.get_unverified_header(token)
        kid = headers.get('kid')
        logger.info(f"Token kid: {kid}")

        if not kid:
            logger.error("Token missing 'kid' header")
            raise HTTPException(status_code=401, detail="Token missing 'kid' header")

        # Find the matching public key
        key = None
        for k in keys.get('keys', []):
            if k['kid'] == kid:
                key = k
                break

        if not key:
            logger.error(f"Public key not found for kid: {kid}")
            raise HTTPException(status_code=401, detail="Public key not found for token")

        logger.info(f"Found matching public key for kid: {kid}")

        # Verify and decode token
        logger.info("Verifying and decoding token")
        logger.info(f"Cognito config - Region: {COGNITO_REGION}, Pool: {COGNITO_USER_POOL_ID}, Client: {COGNITO_CLIENT_ID}")

        claims = jose_jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience=COGNITO_CLIENT_ID,
            issuer=f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}',
            options={'verify_at_hash': False}  # Skip at_hash validation since we only use ID token
        )
        logger.info(f"Token successfully decoded. Claims: {list(claims.keys())}")

        # Extract user info from token
        cognito_username = claims.get('cognito:username')
        email = claims.get('email')
        logger.info(f"Extracted user info - username: {cognito_username}, email: {email}")

        if not cognito_username:
            logger.error("Token missing cognito:username claim")
            raise HTTPException(status_code=401, detail="Token missing cognito:username")

        # Get or create user in database
        logger.info(f"Looking up user in database: {cognito_username}")
        user_repo = UserRepository(db)
        user = await user_repo.get_by_cognito_username(cognito_username)

        if not user:
            logger.info(f"User not found, creating new user: {cognito_username}")
            # Auto-create user from Cognito token (first login)
            user = await user_repo.create_from_cognito(
                cognito_username=cognito_username,
                email=email or f"{cognito_username}@unknown.local",
                namespace=f"@{cognito_username}"
            )
            logger.info(f"Created new user with ID: {user.user_id}")
        else:
            logger.info(f"Found existing user with ID: {user.user_id}")

        return user

    except JWTError as e:
        logger.error(f"JWT verification failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during JWT verification: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
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
