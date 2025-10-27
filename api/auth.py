"""API authentication and authorization."""

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()

# Hardcoded API keys mapping to namespaces
# TODO: Replace with database lookup when auth system is ready
VALID_API_KEYS = {
    "gp_dev_hardcoded": "@goldenpathdev"
}


def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify API key and return associated namespace.

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
