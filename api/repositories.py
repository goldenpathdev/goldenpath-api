"""Repository pattern for database operations."""
import secrets
import bcrypt
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import User, APIKey


class UserRepository:
    """Repository for User database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_namespace(self, namespace: str) -> Optional[User]:
        """Get user by namespace."""
        result = await self.db.execute(
            select(User).where(User.namespace == namespace)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: str,
        email: str,
        namespace: str,
        auth_provider: str,
        email_verified: bool = False,
        name: Optional[str] = None,
        bio: Optional[str] = None,
        github_username: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        user = User(
            user_id=user_id,
            email=email,
            email_verified=email_verified,
            name=name,
            namespace=namespace,
            bio=bio,
            github_username=github_username,
            auth_provider=auth_provider,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_cognito_username(self, cognito_username: str) -> Optional[User]:
        """
        Get user by Cognito username (sub claim from JWT).
        Note: In our model, cognito username is stored as user_id.
        """
        return await self.get_by_id(cognito_username)

    async def create_from_cognito(
        self,
        cognito_username: str,
        email: str,
        namespace: str,
    ) -> User:
        """
        Create user from Cognito JWT on first login.

        If a user with this email already exists (e.g., from OAuth signup),
        link this Cognito account to the existing user record by updating
        the user_id to match the Cognito username.

        Args:
            cognito_username: Cognito sub claim (unique user ID)
            email: User email from JWT
            namespace: Generated namespace (@username)
        """
        # Check if user with this email already exists
        existing_user = await self.get_by_email(email)

        if existing_user:
            # User exists from OAuth - link this Cognito account to existing record
            # Update the user_id to match Cognito username for future lookups
            await self.db.execute(
                update(User)
                .where(User.email == email)
                .values(
                    user_id=cognito_username,
                    email_verified=True,  # Cognito verified
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            return await self.get_by_id(cognito_username)

        # New user - create normally
        return await self.create(
            user_id=cognito_username,
            email=email,
            namespace=namespace,
            auth_provider="cognito",
            email_verified=True,  # Cognito has already verified
        )

    async def update(
        self,
        user_id: str,
        name: Optional[str] = None,
        bio: Optional[str] = None,
        github_username: Optional[str] = None,
    ) -> Optional[User]:
        """Update user profile."""
        # Build update dict with only provided values
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if bio is not None:
            update_data["bio"] = bio
        if github_username is not None:
            update_data["github_username"] = github_username

        if not update_data:
            # No updates provided, just return existing user
            return await self.get_by_id(user_id)

        update_data["updated_at"] = datetime.utcnow()

        await self.db.execute(
            update(User).where(User.user_id == user_id).values(**update_data)
        )
        await self.db.commit()

        return await self.get_by_id(user_id)


class APIKeyRepository:
    """Repository for API Key database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, key_id: str) -> Optional[APIKey]:
        """Get API key by ID."""
        result = await self.db.execute(
            select(APIKey).where(APIKey.key_id == key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash."""
        result = await self.db.execute(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> List[APIKey]:
        """List all API keys for a user."""
        result = await self.db.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        user_id: str,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_days: int = 90,
    ) -> Tuple[str, APIKey]:
        """
        Create a new API key.

        Args:
            user_id: User ID to associate with the key
            name: Display name for the key
            scopes: List of scopes (default: ["read", "write"])
            expires_days: Days until expiration (default: 90)

        Returns:
            Tuple of (plaintext_api_key, api_key_record)
            WARNING: The plaintext key is only returned once!
        """
        # Generate API key
        api_key = f"gp_live_{secrets.token_urlsafe(32)}"

        # Hash the key for storage
        key_hash = bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()

        # Create prefix for display
        key_prefix = api_key[:16] + "..."

        # Default scopes
        if scopes is None:
            scopes = ["read", "write"]

        # Calculate expiration (use timezone-aware datetime to match DB timestamps)
        from datetime import timedelta, timezone
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

        # Create record
        key_record = APIKey(
            key_id=f"key_{secrets.token_urlsafe(16)}",
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes,
            expires_at=expires_at,
        )

        self.db.add(key_record)
        await self.db.commit()
        await self.db.refresh(key_record)

        return api_key, key_record

    async def verify_key(self, api_key: str) -> Optional[APIKey]:
        """
        Verify an API key and return the key record if valid.
        Also updates last_used timestamp.
        Returns None if key is invalid, inactive, or expired.
        """
        # Get all active keys (we need to check hash against all)
        result = await self.db.execute(
            select(APIKey).where(APIKey.is_active == True)
        )
        keys = result.scalars().all()

        # Check each key's hash
        for key_record in keys:
            if bcrypt.checkpw(api_key.encode(), key_record.key_hash.encode()):
                # Check if key has expired (use timezone-aware datetime)
                from datetime import timezone
                now = datetime.now(timezone.utc)
                if key_record.expires_at and key_record.expires_at < now:
                    # Key has expired - return None without updating last_used
                    return None

                # Update last_used timestamp
                await self.db.execute(
                    update(APIKey)
                    .where(APIKey.key_id == key_record.key_id)
                    .values(last_used=now)
                )
                await self.db.commit()
                await self.db.refresh(key_record)
                return key_record

        return None

    async def delete(self, key_id: str, user_id: str) -> bool:
        """Delete an API key (must match user_id for security)."""
        result = await self.db.execute(
            delete(APIKey)
            .where(APIKey.key_id == key_id)
            .where(APIKey.user_id == user_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def deactivate(self, key_id: str, user_id: str) -> bool:
        """Deactivate an API key instead of deleting it."""
        result = await self.db.execute(
            update(APIKey)
            .where(APIKey.key_id == key_id)
            .where(APIKey.user_id == user_id)
            .values(is_active=False)
        )
        await self.db.commit()
        return result.rowcount > 0
