"""
Authentication endpoints for user registration, login, and token management.

This module provides REST API endpoints for user authentication,
registration, and JWT token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from backend.db.database import get_db_session
from backend.db.schemas import (
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    ErrorResponse,
)
from backend.services.auth_service import AuthService
from backend.services.auth_dependencies import (
    get_auth_service,
    CurrentUser,
    RequireSuperAdmin,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        409: {"model": ErrorResponse, "description": "User already exists"},
    },
)
async def register_user(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Register a new user.
    
    Args:
        user_data: User registration data
        auth_service: Authentication service
        
    Returns:
        UserResponse: Created user information
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        user = await auth_service.create_user(user_data)
        
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            language_preference=user.language_preference,
            organization_id=user.organization_id,
            created_at=user.created_at,
            last_login=user.last_login,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication failed"},
    },
)
async def login_user(
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate user and return access token.
    
    Args:
        login_data: Login credentials
        auth_service: Authentication service
        
    Returns:
        TokenResponse: Access token and user information
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        return await auth_service.login_user(login_data.email, login_data.password)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid refresh token"},
    },
)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Refresh access token using refresh token.
    
    Args:
        refresh_token: Valid refresh token
        auth_service: Authentication service
        
    Returns:
        TokenResponse: New access token and user information
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        return await auth_service.refresh_access_token(refresh_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: Current user information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        language_preference=current_user.language_preference,
        organization_id=current_user.organization_id,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.get(
    "/users",
    response_model=list[UserResponse],
    responses={
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
async def list_users(
    current_user: RequireSuperAdmin,
    db: AsyncSession = Depends(get_db_session),
) -> list[UserResponse]:
    """List all users (Super-Admin only).
    
    Args:
        current_user: Current authenticated super-admin user
        db: Database session
        
    Returns:
        list[UserResponse]: List of all users
    """
    from sqlalchemy import select
    from backend.db.models import User
    
    try:
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        return [
            UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                language_preference=user.language_preference,
                organization_id=user.organization_id,
                created_at=user.created_at,
                last_login=user.last_login,
            )
            for user in users
        ]
        
    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.post("/logout")
async def logout_user(current_user: CurrentUser) -> dict:
    """Logout current user.
    
    Note: Since we're using stateless JWT tokens, logout is handled
    client-side by discarding the token. This endpoint exists for
    consistency and future token blacklisting if needed.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: Logout confirmation
    """
    logger.info(f"User {current_user.email} logged out")
    return {"message": "Successfully logged out"}


@router.get(
    "/accessible-businesses",
    response_model=list[str],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def get_accessible_businesses(
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> list[str]:
    """Get list of business IDs accessible to current user.
    
    Args:
        current_user: Current authenticated user
        auth_service: Authentication service
        
    Returns:
        list[str]: List of accessible business IDs
    """
    try:
        business_ids = await auth_service.get_user_accessible_businesses(current_user.id)
        return [str(business_id) for business_id in business_ids]
        
    except Exception as e:
        logger.error(f"Failed to get accessible businesses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve accessible businesses"
        )