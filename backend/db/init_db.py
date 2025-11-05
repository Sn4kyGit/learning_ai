"""
Database initialization utilities.

This module provides functions for initializing the database,
creating test data, and managing database lifecycle.
"""

import asyncio
import logging
from typing import Optional
from uuid import uuid4

from sqlalchemy import select

from backend.db.database import get_db_session_context, init_database
from backend.db.models import Organization, User, Business
from backend.config import get_settings

logger = logging.getLogger(__name__)


async def create_default_organization() -> Optional[str]:
    """Create a default organization for development.
    
    Returns:
        Optional[str]: Organization ID if created, None if already exists
    """
    try:
        async with get_db_session_context() as session:
            # Check if default organization exists
            from sqlalchemy import select
            
            result = await session.execute(
                select(Organization).where(Organization.name == "Default Organization")
            )
            existing_org = result.scalar_one_or_none()
            
            if existing_org:
                logger.info("Default organization already exists")
                return str(existing_org.id)
            
            # Create default organization
            org = Organization(
                id=uuid4(),
                name="Default Organization",
                subscription_tier="basic",
                cost_limit_monthly=100.00
            )
            session.add(org)
            await session.commit()
            
            logger.info(f"Created default organization: {org.id}")
            return str(org.id)
            
    except Exception as e:
        logger.error(f"Error creating default organization: {e}")
        return None


async def create_admin_user(
    email: str = "admin@example.com",
    password: str = "admin123",
    name: str = "System Administrator"
) -> Optional[str]:
    """Create an admin user for development.
    
    Args:
        email: Admin email address
        password: Admin password (will be hashed)
        name: Admin display name
        
    Returns:
        Optional[str]: User ID if created, None if already exists or error
    """
    try:
        async with get_db_session_context() as session:
            from sqlalchemy import select
            from passlib.context import CryptContext
            
            # Check if admin user exists
            result = await session.execute(
                select(User).where(User.email == email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.info(f"Admin user {email} already exists")
                return str(existing_user.id)
            
            # Get or create default organization
            org_id = await create_default_organization()
            if not org_id:
                logger.error("Could not create or find default organization")
                return None
            
            # Hash password using the same method as AuthService
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
            password_hash = pwd_context.hash(password)
            
            # Create admin user
            from uuid import UUID
            user = User(
                id=uuid4(),
                email=email,
                name=name,
                role="super_admin",
                language_preference="en",
                organization_id=UUID(org_id) if isinstance(org_id, str) else org_id,
                password_hash=password_hash
            )
            session.add(user)
            await session.commit()
            
            logger.info(f"Created admin user: {user.id} ({email})")
            return str(user.id)
            
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        return None


async def create_sample_business(
    name: str = "Sample Restaurant",
    google_place_id: str = "sample_place_123",
    organization_id: Optional[str] = None
) -> Optional[str]:
    """Create a sample business for development.
    
    Args:
        name: Business name
        google_place_id: Google Places ID
        organization_id: Organization ID (will use default if None)
        
    Returns:
        Optional[str]: Business ID if created, None if error
    """
    try:
        async with get_db_session_context() as session:
            from sqlalchemy import select
            
            # Check if business exists
            result = await session.execute(
                select(Business).where(Business.google_place_id == google_place_id)
            )
            existing_business = result.scalar_one_or_none()
            
            if existing_business:
                logger.info(f"Sample business {name} already exists")
                return str(existing_business.id)
            
            # Get organization ID
            if not organization_id:
                organization_id = await create_default_organization()
                if not organization_id:
                    logger.error("Could not create or find default organization")
                    return None
            
            # Create sample business
            from uuid import UUID
            business = Business(
                id=uuid4(),
                organization_id=UUID(organization_id) if isinstance(organization_id, str) else organization_id,
                name=name,
                google_place_id=google_place_id,
                category="restaurant",
                address="123 Sample Street, Sample City",
                avg_rating=4.2,
                total_reviews=0
            )
            session.add(business)
            await session.commit()
            
            logger.info(f"Created sample business: {business.id} ({name})")
            return str(business.id)
            
    except Exception as e:
        logger.error(f"Error creating sample business: {e}")
        return None


async def initialize_development_data():
    """Initialize development data including default org, admin user, and sample business."""
    logger.info("Initializing development data...")
    
    try:
        # Initialize database
        await init_database()
        
        # Create default organization
        org_id = await create_default_organization()
        if not org_id:
            logger.error("Failed to create default organization")
            return False
        
        # Create admin user
        user_id = await create_admin_user()
        if not user_id:
            logger.error("Failed to create admin user")
            return False
        
        # Create sample business
        business_id = await create_sample_business(organization_id=org_id)
        if not business_id:
            logger.error("Failed to create sample business")
            return False
        
        logger.info("Development data initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing development data: {e}")
        return False


async def reset_database():
    """Reset database by dropping and recreating all tables."""
    logger.warning("Resetting database - all data will be lost!")
    
    try:
        from backend.db.database import engine, Base
        
        if engine is None:
            from backend.db.database import create_database_engine
            engine = create_database_engine()
        
        # Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("All tables dropped")
        
        # Recreate tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("All tables recreated")
        
        # Initialize development data
        await initialize_development_data()
        
        logger.info("Database reset completed")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False


if __name__ == "__main__":
    # Run initialization when script is executed directly
    logging.basicConfig(level=logging.INFO)
    
    settings = get_settings()
    if settings.environment == "development":
        asyncio.run(initialize_development_data())
    else:
        logger.warning("Database initialization skipped - not in development environment")