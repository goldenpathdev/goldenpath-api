"""Pydantic schemas for API requests and responses."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# User Schemas
class UserRegisterRequest(BaseModel):
    """Request body for user registration."""
    user_id: str = Field(..., description="Cognito user ID (sub)")
    email: EmailStr
    email_verified: bool = False
    name: Optional[str] = None
    auth_provider: str = Field(..., description="google|email|github")


class UserUpdateRequest(BaseModel):
    """Request body for updating user profile."""
    name: Optional[str] = None
    bio: Optional[str] = None
    github_username: Optional[str] = None


class UserResponse(BaseModel):
    """User profile response."""
    user_id: str
    email: str
    email_verified: bool
    name: Optional[str]
    namespace: str
    bio: Optional[str]
    github_username: Optional[str]
    auth_provider: str
    subscription_tier: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserRegisterResponse(BaseModel):
    """Response for user registration."""
    user_id: str
    email: str
    email_verified: bool
    namespace: str
    auth_provider: str
    default_api_key: Optional[str] = Field(
        None, description="Only provided if email_verified=true"
    )
    message: Optional[str] = None


# API Key Schemas
class APIKeyCreateRequest(BaseModel):
    """Request body for creating an API key."""
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable key name")
    scopes: Optional[List[str]] = Field(default=["read", "write"], description="Permission scopes")


class APIKeyResponse(BaseModel):
    """API key metadata (without the actual key)."""
    key_id: str
    user_id: str
    name: str
    key_prefix: str
    scopes: List[str]
    created_at: datetime
    last_used: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """Response for creating an API key (includes plaintext key once)."""
    key_id: str
    name: str
    api_key: str = Field(..., description="The actual API key - save this! It won't be shown again")
    key_prefix: str
    scopes: List[str]
    created_at: datetime
    message: str = "Save this API key securely. You won't be able to see it again."


class APIKeyListResponse(BaseModel):
    """Response for listing API keys."""
    api_keys: List[APIKeyResponse]
    total: int


# Error Schemas
class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    status_code: int
