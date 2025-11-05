"""
User management service for multi-tenant business access control.

This module provides functionality for managing user access to businesses,
organizations, and role-based permissions.
"""

from typing import List, Optional
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException, status

from backend.db.models import User, Business, Organization, UserBusinessAccess
from backend.db.schemas import UserResponse

logger = logging.getLogger(__name__)


class UserManagementService:
    """Service for managing user access and permissions."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def grant_business_access(
        self,
        user_id: UUID,
        business_id: UUID,
        permission_level: str,
        granted_by_user_id: UUID,
    ) -> UserBusinessAccess:
        """Grant user access to a business.
        
        Args:
            user_id: User to grant access to
            business_id: Business to grant access to
            permission_level: Permission level (read_only, full_access)
            granted_by_user_id: User granting the access
            
        Returns:
            UserBusinessAccess: Created access record
            
        Raises:
            HTTPException: If validation fails
        """
        # Validate user exists
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Validate business exists
        business_result = await self.db.execute(
            select(Business).where(Business.id == business_id)
        )
        business = business_result.scalar_one_or_none()
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )

        # Validate permission level
        if permission_level not in ["read_only", "full_access"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid permission level"
            )

        # Check if access already exists
        existing_access = await self.db.execute(
            select(UserBusinessAccess).where(
                UserBusinessAccess.user_id == user_id,
                UserBusinessAccess.business_id == business_id
            )
        )
        if existing_access.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has access to this business"
            )

        # Create access record
        access = UserBusinessAccess(
            user_id=user_id,
            business_id=business_id,
            permission_level=permission_level,
            granted_by=granted_by_user_id,
        )

        self.db.add(access)
        await self.db.commit()
        await self.db.refresh(access)

        logger.info(
            f"Granted {permission_level} access to business {business_id} "
            f"for user {user_id} by user {granted_by_user_id}"
        )

        return access

    async def revoke_business_access(
        self,
        user_id: UUID,
        business_id: UUID,
    ) -> bool:
        """Revoke user access to a business.
        
        Args:
            user_id: User to revoke access from
            business_id: Business to revoke access to
            
        Returns:
            bool: True if access was revoked, False if no access existed
        """
        result = await self.db.execute(
            delete(UserBusinessAccess).where(
                UserBusinessAccess.user_id == user_id,
                UserBusinessAccess.business_id == business_id
            )
        )

        await self.db.commit()

        revoked = result.rowcount > 0
        if revoked:
            logger.info(f"Revoked business {business_id} access for user {user_id}")

        return revoked

    async def update_business_access(
        self,
        user_id: UUID,
        business_id: UUID,
        permission_level: str,
    ) -> UserBusinessAccess:
        """Update user's permission level for a business.
        
        Args:
            user_id: User ID
            business_id: Business ID
            permission_level: New permission level
            
        Returns:
            UserBusinessAccess: Updated access record
            
        Raises:
            HTTPException: If access record not found or validation fails
        """
        # Validate permission level
        if permission_level not in ["read_only", "full_access"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid permission level"
            )

        # Get existing access record
        result = await self.db.execute(
            select(UserBusinessAccess).where(
                UserBusinessAccess.user_id == user_id,
                UserBusinessAccess.business_id == business_id
            )
        )
        access = result.scalar_one_or_none()

        if not access:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User access record not found"
            )

        # Update permission level
        access.permission_level = permission_level
        await self.db.commit()
        await self.db.refresh(access)

        logger.info(
            f"Updated business {business_id} access for user {user_id} "
            f"to {permission_level}"
        )

        return access

    async def get_business_users(self, business_id: UUID) -> List[dict]:
        """Get all users with access to a business.
        
        Args:
            business_id: Business ID
            
        Returns:
            List[dict]: List of users with their access levels
        """
        result = await self.db.execute(
            select(User, UserBusinessAccess.permission_level)
            .join(UserBusinessAccess, User.id == UserBusinessAccess.user_id)
            .where(UserBusinessAccess.business_id == business_id)
        )

        users = []
        for user, permission_level in result.fetchall():
            users.append({
                "user": UserResponse(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                    role=user.role,
                    language_preference=user.language_preference,
                    organization_id=user.organization_id,
                    created_at=user.created_at,
                    last_login=user.last_login,
                ),
                "permission_level": permission_level,
            })

        return users

    async def get_user_businesses(self, user_id: UUID) -> List[dict]:
        """Get all businesses accessible to a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List[dict]: List of businesses with access levels
        """
        # First check if user is super_admin
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return []

        if user.role == "super_admin":
            # Super-admins have access to all businesses
            result = await self.db.execute(select(Business))
            businesses = result.scalars().all()
            
            return [
                {
                    "business": {
                        "id": str(business.id),
                        "name": business.name,
                        "google_place_id": business.google_place_id,
                        "category": business.category,
                        "address": business.address,
                        "avg_rating": business.avg_rating,
                        "total_reviews": business.total_reviews,
                    },
                    "permission_level": "full_access",
                }
                for business in businesses
            ]

        # Get businesses with explicit access
        result = await self.db.execute(
            select(Business, UserBusinessAccess.permission_level)
            .join(UserBusinessAccess, Business.id == UserBusinessAccess.business_id)
            .where(UserBusinessAccess.user_id == user_id)
        )

        businesses = []
        for business, permission_level in result.fetchall():
            businesses.append({
                "business": {
                    "id": str(business.id),
                    "name": business.name,
                    "google_place_id": business.google_place_id,
                    "category": business.category,
                    "address": business.address,
                    "avg_rating": business.avg_rating,
                    "total_reviews": business.total_reviews,
                },
                "permission_level": permission_level,
            })

        return businesses

    async def get_organization_users(self, organization_id: UUID) -> List[UserResponse]:
        """Get all users in an organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            List[UserResponse]: List of users in the organization
        """
        result = await self.db.execute(
            select(User).where(User.organization_id == organization_id)
        )
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

    async def bulk_grant_organization_access(
        self,
        organization_id: UUID,
        business_id: UUID,
        permission_level: str,
        granted_by_user_id: UUID,
    ) -> int:
        """Grant all users in an organization access to a business.
        
        Args:
            organization_id: Organization ID
            business_id: Business ID
            permission_level: Permission level to grant
            granted_by_user_id: User granting the access
            
        Returns:
            int: Number of users granted access
        """
        # Get all users in the organization
        users = await self.get_organization_users(organization_id)
        
        granted_count = 0
        for user_response in users:
            try:
                await self.grant_business_access(
                    user_response.id,
                    business_id,
                    permission_level,
                    granted_by_user_id,
                )
                granted_count += 1
            except HTTPException:
                # Skip users who already have access
                continue

        logger.info(
            f"Bulk granted {permission_level} access to business {business_id} "
            f"for {granted_count} users in organization {organization_id}"
        )

        return granted_count