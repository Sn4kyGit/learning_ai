"""
Authentication dependencies for FastAPI endpoints.

This module provides dependency injection functions for authentication
and authorization in FastAPI routes.
"""

from typing import Optional, Annotated
from uuid import UUID
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.db.models import User
from backend.services.auth_service import AuthService, AuthenticationError

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_auth_service(db: AsyncSession = Depends(get_db_session)) -> AuthService:
    """Get authentication service instance.
    
    Args:
        db: Database session
        
    Returns:
        AuthService: Authentication service instance
    """
    return AuthService(db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        auth_service: Authentication service
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Verify token
        payload = auth_service.verify_token(credentials.credentials, "access")
        user_id = UUID(payload.get("sub"))
        
        # Get user from database
        user = await auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user
        
    except (AuthenticationError, ValueError) as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (placeholder for future user status checks).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    # TODO: Add user status checks (active/inactive, suspended, etc.)
    return current_user


def require_role(required_role: str):
    """Create dependency that requires specific user role.
    
    Args:
        required_role: Required user role (super_admin, admin, viewer)
        
    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        role_hierarchy = {
            "viewer": 1,
            "admin": 2,
            "super_admin": 3
        }
        
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 999)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
            
        return current_user
    
    return role_checker


def require_business_access(business_id_param: str = "business_id", permission: str = "read_only"):
    """Create dependency that requires access to specific business.
    
    Args:
        business_id_param: Name of path parameter containing business ID
        permission: Required permission level (read_only, full_access)
        
    Returns:
        Dependency function
    """
    async def business_access_checker(
        business_id: UUID,
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        has_access = await auth_service.check_user_business_access(
            current_user.id, business_id, permission
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this business"
            )
            
        return current_user
    
    return business_access_checker


# Common role dependencies
RequireSuperAdmin = Annotated[User, Depends(require_role("super_admin"))]
RequireAdmin = Annotated[User, Depends(require_role("admin"))]
RequireViewer = Annotated[User, Depends(require_role("viewer"))]

# Current user dependencies
CurrentUser = Annotated[User, Depends(get_current_active_user)]
OptionalCurrentUser = Annotated[Optional[User], Depends(get_current_user)]