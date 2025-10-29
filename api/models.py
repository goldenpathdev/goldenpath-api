"""Database models for Golden Path application."""
from sqlalchemy import Column, String, Boolean, Integer, TIMESTAMP, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User account model."""

    __tablename__ = 'users'

    user_id = Column(String(255), primary_key=True, comment="Cognito user ID (sub)")
    email = Column(String(255), unique=True, nullable=False, comment="User email address")
    email_verified = Column(Boolean, default=False, nullable=False, comment="Email verification status")
    name = Column(String(255), comment="User display name")
    namespace = Column(String(100), unique=True, nullable=False, comment="User namespace (@username)")
    bio = Column(Text, comment="User bio/description")
    github_username = Column(String(100), comment="GitHub username")
    auth_provider = Column(String(50), nullable=False, comment="Authentication provider: google|email|github")
    subscription_tier = Column(String(50), default='free', nullable=False, comment="Subscription tier: free|teams|enterprise")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_namespace', 'namespace'),
        Index('idx_users_email_verified', 'email_verified'),
    )

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', email='{self.email}', namespace='{self.namespace}')>"


class APIKey(Base):
    """API key model for MCP client authentication."""

    __tablename__ = 'api_keys'

    key_id = Column(String(100), primary_key=True, comment="Unique key identifier")
    user_id = Column(String(255), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, comment="Owner user ID")
    name = Column(String(255), nullable=False, comment="Human-readable key name")
    key_hash = Column(String(255), unique=True, nullable=False, comment="bcrypt hash of API key")
    key_prefix = Column(String(20), nullable=False, comment="Key prefix for display (gp_live_xxx...)")
    scopes = Column(JSONB, default=["read", "write"], nullable=False, comment="Permission scopes")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_used = Column(TIMESTAMP(timezone=True), comment="Last time this key was used")
    expires_at = Column(TIMESTAMP(timezone=True), comment="Key expiration time")
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether key is active")

    __table_args__ = (
        Index('idx_api_keys_user_id', 'user_id'),
        Index('idx_api_keys_key_hash', 'key_hash'),
        Index('idx_api_keys_is_active', 'is_active'),
    )

    def __repr__(self):
        return f"<APIKey(key_id='{self.key_id}', name='{self.name}', user_id='{self.user_id}')>"


class GoldenPathMetadata(Base):
    """Optional metadata for Golden Paths (S3 remains source of truth)."""

    __tablename__ = 'golden_paths_metadata'

    path_id = Column(String(100), primary_key=True, comment="Unique path identifier")
    namespace = Column(String(100), nullable=False, comment="Path namespace (@username or @org)")
    name = Column(String(100), nullable=False, comment="Path name (kebab-case)")
    version = Column(String(20), nullable=False, comment="Semantic version")
    owner_user_id = Column(String(255), ForeignKey('users.user_id', ondelete='SET NULL'), comment="Owner user ID")
    description = Column(Text, comment="Path description")
    tags = Column(JSONB, default=[], comment="Search tags")
    download_count = Column(Integer, default=0, nullable=False, comment="Total downloads")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_public = Column(Boolean, default=True, nullable=False, comment="Public vs private path")

    __table_args__ = (
        Index('idx_golden_paths_namespace_name', 'namespace', 'name'),
        Index('idx_golden_paths_owner', 'owner_user_id'),
        Index('idx_golden_paths_public', 'is_public'),
    )

    def __repr__(self):
        return f"<GoldenPathMetadata(namespace='{self.namespace}', name='{self.name}', version='{self.version}')>"
