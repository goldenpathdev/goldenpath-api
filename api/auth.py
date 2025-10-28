"""API authentication and authorization."""

from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# Hardcoded API keys mapping to namespaces
# TODO: Replace with database lookup when auth system is ready
VALID_API_KEYS = {
    "gp_dev_hardcoded": "@goldenpathdev"
}


def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify API key and return associated namespace (required).

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        Namespace string (e.g., "@goldenpathdev")

    Raises:
        HTTPException: If API key is invalid
    """
    api_key = credentials.credentials

    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return VALID_API_KEYS[api_key]


def optional_verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security)
) -> Optional[str]:
    """
    Verify API key and return associated namespace (optional).

    Args:
        credentials: HTTP Bearer token credentials (optional)

    Returns:
        Namespace string if valid API key provided, None otherwise
    """
    if credentials is None:
        return None

    api_key = credentials.credentials

    if api_key in VALID_API_KEYS:
        return VALID_API_KEYS[api_key]

    return None
