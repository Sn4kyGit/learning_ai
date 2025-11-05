"""
Unit tests for user management service.

This module tests multi-tenant access control and business
permission management functionality.
"""

import pytest
from uuid import uuid4
from fastapi import HTTPException, status

from backend.services.user_management_service import UserManagementService
from backend.db.models import User, Business, Organization, UserBusinessAccess


class TestUserManagementService:
    """Test suite for UserManagementService."""

    @pytest.mark.asyncio
    async def test_grant_business_access_success(self, test_db_session, test_organization):
        """Test successful business access granting."""
        # Arrange
        service = UserManagementService(test_db_session)
        
        # Create user and business
        user = User(
            email="user@example.com",
            name="Test User",
            role="admin",
            organization_id=test_organization.id,
            password_hash="hashed_password"
        )
        
        business = Business(
            name="Test Restaurant",
            google_place_id="test-place-123",
            organization_id=test_organization.id
        )
        
        granter = User(
            email="granter@example.com",
            name="Granter User",
            role="super_admin",
            password_hash="hashed_password"
        )
        
        test_db_session.add_all([user, business, granter])
        await test_db_session.commit()
        await test_db_session.refresh(user)
        await test_db_session.refresh(business)
        await test_db_session.refresh(granter)
        
        # Act
        access = await service.grant_business_access(
            user.id,
            business.id,
            "read_only",
            granter.id
        )
        
        # Assert
        assert access.user_id == user.id
        assert access.business_id == business.id
        assert access.permission_level == "read_only"
        assert access.granted_by == granter.id

    @pytest.mark.asyncio
    async def test_grant_business_access_user_not_found(self, test_db_session):
        """Test granting access to non-existent user."""
        # Arrange
        service = UserManagementService(test_db_session)
        non_existent_user_id = uuid4()
        business_id = uuid4()
        granter_id = uuid4()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.grant_business_access(
                non_existent_user_id,
                business_id,
                "read_only",
                granter_id
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_grant_business_access_business_not_found(self, test_db_session):
        """Test granting access to non-existent business."""
        # Arrange
        service = UserManagementService(test_db_session)
        
        user = User(
            email="user@example.com",
            name="Test User",
            role="admin",
            password_hash="hashed_password"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        non_existent_business_id = uuid4()
        granter_id = uuid4()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.grant_business_access(
                user.id,
                non_existent_business_id,
                "read_only",
                granter_id
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Business not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_grant_business_access_invalid_permission(self, test_db_session, test_organization):
        """Test granting access with invalid permission level."""
        # Arrange
        service = UserManagementService(test_db_session)
        
        user = User(
            email="user@example.com",
            name="Test User",
            role="admin",
            password_hash="hashed_password"
        )
        
        business = Business(
            name="Test Restaurant",
            google_place_id="test-place-123",
            organization_id=test_organization.id
        )
        
        test_db_session.add_all([user, business])
        await test_db_session.commit()
        await test_db_session.refresh(user)
        await test_db_session.refresh(business)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.grant_business_access(
                user.id,
                business.id,
                "invalid_permission",
                uuid4()
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid permission level" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_grant_business_access_already_exists(self, test_db_session, test_organization):
        """Test granting access when access already exists."""
        # Arrange
        service = UserManagementService(test_db_session)
        
        user = User(
            email="user@example.com",
            name="Test User",
            role="admin",
            password_hash="hashed_password"
        )
        
        business = Business(
            name="Test Restaurant",
            google_place_id="test-place-123",
            organization_id=test_organization.id
        )
        
        granter = User(
            email="granter@example.com",
            name="Granter User",
            role="super_admin",
            password_hash="hashed_password"
        )
        
        test_db_session.add_all([user, business, granter])
        await test_db_session.commit()
        await test_db_session.refresh(user)
        await test_db_session.refresh(business)
        await test_db_session.refresh(granter)
        
        # Create existing access
        existing_access = UserBusinessAccess(
            user_id=user.id,
            business_id=business.id,
            permission_level="read_only",
            granted_by=granter.id
        )
        test_db_session.add(existing_access)
        await test_db_session.commit()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.grant_business_access(
                user.id,
                business.id,
                "full_access",
                granter.id
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already has access" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_revoke_business_access_success(self, test_db_session, test_organization):
        """Test successful business access revocation."""
        # Arrange
        service = UserManagementService(test_db_session)
        
        user = User(
            email="user@example.com",
            name="Test User",
            role="admin",
            password_hash="hashed_password"
        )
        
        business = Business(
            name="Test Restaurant",
            google_place_id="test-place-123",
            organization_id=test_organization.id
        )
        
        test_db_session.add_all([user, business])
        await test_db_session.commit()
        await test_db_session.refresh(user)
        await test_db_session.refresh(business)
        
        # Create access to revoke
        access = UserBusinessAccess(
            user_id=user.id,
            business_id=business.id,
            permission_level="read_only",
            granted_by=uuid4()
        )
        test_db_session.add(access)
        await test_db_session.commit()
        
        # Act
        result = await service.revoke_business_access(user.id, business.id)
        
        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_business_access_not_found(self, test_db_session):
        """Test revoking non-existent business access."""
        # Arrange
        service = UserManagementService(test_db_session)
        user_id = uuid4()
        business_id = uuid4()
        
        # Act
        result = await service.revoke_business_access(user_id, business_id)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_update_business_access_success(self, test_db_session, test_organization):
        """Test successful business access update."""
        # Arrange
        service = UserManagementService(test_db_session)
        
        user = User(
            email="user@example.com",
            name="Test User",
            role="admin",
            password_hash="hashed_password"
        )
        
        business = Business(
            name="Test Restaurant",
            google_place_id="test-place-123",
            organization_id=test_organization.id
        )
        
        test_db_session.add_all([user, business])
        await test_db_session.commit()
        await test_db_session.refresh(user)
        await test_db_session.refresh(business)
        
        # Create access to update
        access = UserBusinessAccess(
            user_id=user.id,
            business_id=business.id,
            permission_level="read_only",
            granted_by=uuid4()
        )
        test_db_session.add(access)
        await test_db_session.commit()
        
        # Act
        updated_access = await service.update_business_access(
            user.id,
            business.id,
            "full_access"
        )
        
        # Assert
        assert updated_access.permission_level == "full_access"

    @pytest.mark.asyncio
    async def test_update_business_access_not_found(self, test_db_session):
        """Test updating non-existent business access."""
        # Arrange
        service = UserManagementService(test_db_session)
        user_id = uuid4()
        business_id = uuid4()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update_business_access(
                user_id,
                business_id,
                "full_access"
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "access record not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_business_users(self, test_db_session, test_organization):
        """Test getting users with access to a business."""
        # Arrange
        service = UserManagementService(test_db_session)
        
        # Create users and business
        user1 = User(
            email="user1@example.com",
            name="User One",
            role="admin",
            password_hash="hashed_password"
        )
        
        user2 = User(
            email="user2@example.com",
            name="User Two",
            role="viewer",
            password_hash="hashed_password"
        )
        
        business = Business(
            name="Test Restaurant",
            google_place_id="test-place-123",
            organization_id=test_organization.id
        )
        
        test_db_session.add_all([user1, user2, business])
        await test_db_session.commit()
        await test_db_session.refresh(user1)
        await test_db_session.refresh(user2)
        await test_db_session.refresh(business)
        
        # Create access records
        access1 = UserBusinessAccess(
            user_id=user1.id,
            business_id=business.id,
            permission_level="full_access",
            granted_by=uuid4()
        )
        
        access2 = UserBusinessAccess(
            user_id=user2.id,
            business_id=business.id,
            permission_level="read_only",
            granted_by=uuid4()
        )
        
        test_db_session.add_all([access1, access2])
        await test_db_session.commit()
        
        # Act
        users = await service.get_business_users(business.id)
        
        # Assert
        assert len(users) == 2
        user_emails = [user_data["user"].email for user_data in users]
        assert "user1@example.com" in user_emails
        assert "user2@example.com" in user_emails

    @pytest.mark.asyncio
    async def test_get_user_businesses_super_admin(self, test_db_session, test_organization):
        """Test getting businesses for super admin user."""
        # Arrange
        service = UserManagementService(test_db_session)
        
        # Create super admin user
        super_admin = User(
            email="admin@example.com",
            name="Super Admin",
            role="super_admin",
            password_hash="hashed_password"
        )
        
        # Create businesses
        business1 = Business(
            name="Restaurant One",
            google_place_id="place-123",
            organization_id=test_organization.id
        )
        
        business2 = Business(
            name="Restaurant Two",
            google_place_id="place-456",
            organization_id=test_organization.id
        )
        
        test_db_session.add_all([super_admin, business1, business2])
        await test_db_session.commit()
        await test_db_session.refresh(super_admin)
        
        # Act
        businesses = await service.get_user_businesses(super_admin.id)
        
        # Assert
        assert len(businesses) == 2
        business_names = [biz_data["business"]["name"] for biz_data in businesses]
        assert "Restaurant One" in business_names
        assert "Restaurant Two" in business_names
        # Super admin should have full access to all
        for biz_data in businesses:
            assert biz_data["permission_level"] == "full_access"

    @pytest.mark.asyncio
    async def test_get_user_businesses_regular_user(self, test_db_session, test_organization):
        """Test getting businesses for regular user with explicit access."""
        # Arrange
        service = UserManagementService(test_db_session)
        
        # Create regular user
        user = User(
            email="user@example.com",
            name="Regular User",
            role="admin",
            password_hash="hashed_password"
        )
        
        # Create businesses
        business1 = Business(
            name="Restaurant One",
            google_place_id="place-123",
            organization_id=test_organization.id
        )
        
        business2 = Business(
            name="Restaurant Two",
            google_place_id="place-456",
            organization_id=test_organization.id
        )
        
        test_db_session.add_all([user, business1, business2])
        await test_db_session.commit()
        await test_db_session.refresh(user)
        await test_db_session.refresh(business1)
        await test_db_session.refresh(business2)
        
        # Grant access to only one business
        access = UserBusinessAccess(
            user_id=user.id,
            business_id=business1.id,
            permission_level="read_only",
            granted_by=uuid4()
        )
        test_db_session.add(access)
        await test_db_session.commit()
        
        # Act
        businesses = await service.get_user_businesses(user.id)
        
        # Assert
        assert len(businesses) == 1
        assert businesses[0]["business"]["name"] == "Restaurant One"
        assert businesses[0]["permission_level"] == "read_only"

    @pytest.mark.asyncio
    async def test_get_organization_users(self, test_db_session, test_organization):
        """Test getting all users in an organization."""
        # Arrange
        service = UserManagementService(test_db_session)
        
        # Create users in organization
        user1 = User(
            email="user1@example.com",
            name="User One",
            role="admin",
            organization_id=test_organization.id,
            password_hash="hashed_password"
        )
        
        user2 = User(
            email="user2@example.com",
            name="User Two",
            role="viewer",
            organization_id=test_organization.id,
            password_hash="hashed_password"
        )
        
        # Create user in different organization
        other_user = User(
            email="other@example.com",
            name="Other User",
            role="admin",
            password_hash="hashed_password"
        )
        
        test_db_session.add_all([user1, user2, other_user])
        await test_db_session.commit()
        
        # Act
        users = await service.get_organization_users(test_organization.id)
        
        # Assert
        assert len(users) == 2
        user_emails = [user.email for user in users]
        assert "user1@example.com" in user_emails
        assert "user2@example.com" in user_emails
        assert "other@example.com" not in user_emails