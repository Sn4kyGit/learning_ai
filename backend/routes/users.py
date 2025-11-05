"""
User management endpoints for business access control.

This module provides REST API endpoints for managing user access
to businesses and organizations.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging

from backend.db.database import get_db_session
from backend.db.schemas import UserResponse, ErrorResponse
from backend.services.user_management_service import UserManagementService
from backend.services.auth_dependencies import (
    CurrentUser,
    RequireSuperAdmin,
    RequireAdmin,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response schemas
class BusinessAccessRequest(BaseModel):
    """Schema for granting/updating business access."""
    user_id: UUID
    business_id: UUID
    permission_level: str  # read_only, full_access


class BusinessAccessResponse(BaseModel):
    """Schema for business access response."""
    user_id: UUID
    business_id: UUID
    permission_level: str
    granted_at: str
    granted_by: UUID


class BulkAccessRequest(BaseModel):
    """Schema for bulk access granting."""
    organization_id: UUID
    business_id: UUID
    permission_level: str


@router.post(
    "/business-access",
    response_model=BusinessAccessResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "User or business not found"},
    },
)
async def grant_business_access(
    access_request: BusinessAccessRequest,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db_session),
) -> BusinessAccessResponse:
    """Grant user access to a business (Admin+ only).
    
    Args:
        access_request: Business access request data
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        BusinessAccessResponse: Created access record
        
    Raises:
        HTTPException: If validation fails or insufficient permissions
    """
    try:
        service = UserManagementService(db)
        access = await service.grant_business_access(
            access_request.user_id,
            access_request.business_id,
            access_request.permission_level,
            current_user.id,
        )

        return BusinessAccessResponse(
            user_id=access.user_id,
            business_id=access.business_id,
            permission_level=access.permission_level,
            granted_at=access.granted_at.isoformat(),
            granted_by=access.granted_by,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to grant business access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to grant business access"
        )


@router.delete(
    "/business-access/{user_id}/{business_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Access record not found"},
    },
)
async def revoke_business_access(
    user_id: UUID,
    business_id: UUID,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Revoke user access to a business (Admin+ only).
    
    Args:
        user_id: User ID to revoke access from
        business_id: Business ID to revoke access to
        current_user: Current authenticated admin user
        db: Database session
        
    Raises:
        HTTPException: If access record not found or insufficient permissions
    """
    try:
        service = UserManagementService(db)
        revoked = await service.revoke_business_access(user_id, business_id)

        if not revoked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Access record not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke business access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke business access"
        )


@router.put(
    "/business-access",
    response_model=BusinessAccessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Access record not found"},
    },
)
async def update_business_access(
    access_request: BusinessAccessRequest,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db_session),
) -> BusinessAccessResponse:
    """Update user's permission level for a business (Admin+ only).
    
    Args:
        access_request: Business access update data
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        BusinessAccessResponse: Updated access record
        
    Raises:
        HTTPException: If validation fails or insufficient permissions
    """
    try:
        service = UserManagementService(db)
        access = await service.update_business_access(
            access_request.user_id,
            access_request.business_id,
            access_request.permission_level,
        )

        return BusinessAccessResponse(
            user_id=access.user_id,
            business_id=access.business_id,
            permission_level=access.permission_level,
            granted_at=access.granted_at.isoformat(),
            granted_by=access.granted_by,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update business access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update business access"
        )


@router.get(
    "/business/{business_id}/users",
    response_model=List[dict],
    responses={
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Business not found"},
    },
)
async def get_business_users(
    business_id: UUID,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db_session),
) -> List[dict]:
    """Get all users with access to a business (Admin+ only).
    
    Args:
        business_id: Business ID
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        List[dict]: List of users with their access levels
        
    Raises:
        HTTPException: If business not found or insufficient permissions
    """
    try:
        service = UserManagementService(db)
        return await service.get_business_users(business_id)

    except Exception as e:
        logger.error(f"Failed to get business users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business users"
        )


@router.get(
    "/user/{user_id}/businesses",
    response_model=List[dict],
    responses={
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_user_businesses(
    user_id: UUID,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db_session),
) -> List[dict]:
    """Get all businesses accessible to a user (Admin+ only).
    
    Args:
        user_id: User ID
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        List[dict]: List of businesses with access levels
        
    Raises:
        HTTPException: If user not found or insufficient permissions
    """
    try:
        service = UserManagementService(db)
        return await service.get_user_businesses(user_id)

    except Exception as e:
        logger.error(f"Failed to get user businesses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user businesses"
        )


@router.get(
    "/my-businesses",
    response_model=List[dict],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def get_my_businesses(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
) -> List[dict]:
    """Get businesses accessible to current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[dict]: List of businesses with access levels
    """
    try:
        service = UserManagementService(db)
        return await service.get_user_businesses(current_user.id)

    except Exception as e:
        logger.error(f"Failed to get user businesses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve your businesses"
        )


@router.get(
    "/organization/{organization_id}/users",
    response_model=List[UserResponse],
    responses={
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Organization not found"},
    },
)
async def get_organization_users(
    organization_id: UUID,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db_session),
) -> List[UserResponse]:
    """Get all users in an organization (Admin+ only).
    
    Args:
        organization_id: Organization ID
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        List[UserResponse]: List of users in the organization
        
    Raises:
        HTTPException: If organization not found or insufficient permissions
    """
    try:
        service = UserManagementService(db)
        return await service.get_organization_users(organization_id)

    except Exception as e:
        logger.error(f"Failed to get organization users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization users"
        )


@router.post(
    "/bulk-business-access",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Organization or business not found"},
    },
)
async def bulk_grant_organization_access(
    bulk_request: BulkAccessRequest,
    current_user: RequireSuperAdmin,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Grant all users in an organization access to a business (Super-Admin only).
    
    Args:
        bulk_request: Bulk access request data
        current_user: Current authenticated super-admin user
        db: Database session
        
    Returns:
        dict: Number of users granted access
        
    Raises:
        HTTPException: If validation fails or insufficient permissions
    """
    try:
        service = UserManagementService(db)
        granted_count = await service.bulk_grant_organization_access(
            bulk_request.organization_id,
            bulk_request.business_id,
            bulk_request.permission_level,
            current_user.id,
        )

        return {
            "message": f"Granted access to {granted_count} users",
            "granted_count": granted_count,
            "organization_id": str(bulk_request.organization_id),
            "business_id": str(bulk_request.business_id),
            "permission_level": bulk_request.permission_level,
        }

    except Exception as e:
        logger.error(f"Failed to bulk grant organization access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to grant bulk access"
        )