"""
Authentication service for Local Business Intelligence Bot.

This module provides JWT-based authentication, password hashing,
and user management functionality.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.db.models import User, Organization, UserBusinessAccess
from backend.db.schemas import UserCreate, UserResponse, TokenResponse
from backend.config import get_settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT settings
settings = get_settings()
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthenticationError(Exception):
    """Authentication-related errors."""
    pass


class AuthorizationError(Exception):
    """Authorization-related errors."""
    pass


class AuthService:
    """Authentication and authorization service."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using PBKDF2.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database
            
        Returns:
            bool: True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: Dict[str, Any]) -> str:
        """Create JWT access token.
        
        Args:
            data: Token payload data
            
        Returns:
            str: JWT access token
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token.
        
        Args:
            data: Token payload data
            
        Returns:
            str: JWT refresh token
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            token_type: Expected token type (access or refresh)
            
        Returns:
            Dict[str, Any]: Token payload
            
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Verify token type
            if payload.get("type") != token_type:
                raise AuthenticationError("Invalid token type")
                
            # Check expiration
            exp = payload.get("exp")
            if exp is None or datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                raise AuthenticationError("Token expired")
                
            return payload
            
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            Optional[User]: User if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            Optional[User]: User if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            Optional[User]: User if authentication successful, None otherwise
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None
            
        if not self.verify_password(password, user.password_hash):
            return None
            
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await self.db.commit()
        
        return user

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            User: Created user
            
        Raises:
            HTTPException: If user already exists or validation fails
        """
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Validate organization if provided
        if user_data.organization_id:
            org_result = await self.db.execute(
                select(Organization).where(Organization.id == user_data.organization_id)
            )
            if not org_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid organization ID"
                )

        # Create user
        hashed_password = self.hash_password(user_data.password)
        
        user = User(
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
            language_preference=user_data.language_preference,
            organization_id=user_data.organization_id,
            password_hash=hashed_password,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"Created new user: {user.email} with role: {user.role}")
        return user

    async def login_user(self, email: str, password: str) -> TokenResponse:
        """Login user and return tokens.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            TokenResponse: Access token and user info
            
        Raises:
            HTTPException: If authentication fails
        """
        user = await self.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "organization_id": str(user.organization_id) if user.organization_id else None,
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)

        # Convert user to response schema
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            language_preference=user.language_preference,
            organization_id=user.organization_id,
            created_at=user.created_at,
            last_login=user.last_login,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            TokenResponse: New access token and user info
            
        Raises:
            HTTPException: If refresh token is invalid
        """
        try:
            payload = self.verify_token(refresh_token, "refresh")
            user_id = UUID(payload.get("sub"))
            
            user = await self.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            # Create new access token
            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "organization_id": str(user.organization_id) if user.organization_id else None,
            }
            
            access_token = self.create_access_token(token_data)

            user_response = UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                language_preference=user.language_preference,
                organization_id=user.organization_id,
                created_at=user.created_at,
                last_login=user.last_login,
            )

            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user=user_response,
            )

        except AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )

    async def check_user_business_access(
        self, 
        user_id: UUID, 
        business_id: UUID,
        required_permission: str = "read_only"
    ) -> bool:
        """Check if user has access to a specific business.
        
        Args:
            user_id: User UUID
            business_id: Business UUID
            required_permission: Required permission level
            
        Returns:
            bool: True if user has access
        """
        # Get user to check role
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        # Super-admins have access to all businesses
        if user.role == "super_admin":
            return True

        # Check explicit business access
        result = await self.db.execute(
            select(UserBusinessAccess).where(
                UserBusinessAccess.user_id == user_id,
                UserBusinessAccess.business_id == business_id
            )
        )
        access = result.scalar_one_or_none()
        
        if not access:
            return False

        # Check permission level
        if required_permission == "full_access":
            return access.permission_level == "full_access"
        
        # read_only permission is satisfied by both read_only and full_access
        return access.permission_level in ["read_only", "full_access"]

    async def get_user_accessible_businesses(self, user_id: UUID) -> list[UUID]:
        """Get list of business IDs accessible to user.
        
        Args:
            user_id: User UUID
            
        Returns:
            list[UUID]: List of accessible business IDs
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return []

        # Super-admins can access all businesses
        if user.role == "super_admin":
            from backend.db.models import Business
            result = await self.db.execute(select(Business.id))
            return [row[0] for row in result.fetchall()]

        # Get businesses with explicit access
        result = await self.db.execute(
            select(UserBusinessAccess.business_id).where(
                UserBusinessAccess.user_id == user_id
            )
        )
        return [row[0] for row in result.fetchall()]