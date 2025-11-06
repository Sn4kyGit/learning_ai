"""
Database seeding utilities for integration tests.

This module provides utilities for seeding test databases with realistic
data sets for integration testing, performance testing, and E2E scenarios.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import logging

from backend.db.models import (
    Organization, Business, User, Review, Classification,
    UserBusinessAccess, DailyAnalytics, AIUsageLog, MonthlyCostSummary,
    Conversation, ConversationMessage, ReviewResponse
)
from backend.tests.fixtures.data_factories import TestDataFactory

logger = logging.getLogger(__name__)


class DatabaseSeeder:
    """Utility class for seeding test databases with realistic data."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.created_entities = {
            "organizations": [],
            "businesses": [],
            "users": [],
            "reviews": [],
            "classifications": [],
            "user_access": [],
            "analytics": [],
            "ai_logs": [],
            "conversations": [],
            "messages": []
        }
    
    async def seed_basic_scenario(self) -> Dict[str, Any]:
        """Seed database with basic test scenario (1 org, 1 business, few users)."""
        logger.info("Seeding basic test scenario...")
        
        # Create organization
        org = TestDataFactory.create_organization(
            name="Basic Test Organization",
            subscription_tier="premium"
        )
        self.db_session.add(org)
        await self.db_session.commit()
        await self.db_session.refresh(org)
        self.created_entities["organizations"].append(org)
        
        # Create business
        business = TestDataFactory.create_business(
            name="Basic Test Restaurant",
            organization_id=org.id
        )
        self.db_session.add(business)
        await self.db_session.commit()
        await self.db_session.refresh(business)
        self.created_entities["businesses"].append(business)
        
        # Create users
        admin_user = TestDataFactory.create_user(
            email="admin@basic.test",
            name="Admin User",
            role="admin",
            organization_id=org.id
        )
        self.db_session.add(admin_user)
        
        viewer_user = TestDataFactory.create_user(
            email="viewer@basic.test",
            name="Viewer User",
            role="viewer",
            organization_id=org.id
        )
        self.db_session.add(viewer_user)
        
        await self.db_session.commit()
        await self.db_session.refresh(admin_user)
        await self.db_session.refresh(viewer_user)
        
        self.created_entities["users"].extend([admin_user, viewer_user])
        
        # Create user business access
        admin_access = TestDataFactory.create_user_business_access(
            user_id=admin_user.id,
            business_id=business.id,
            permission_level="full_access"
        )
        self.db_session.add(admin_access)
        
        viewer_access = TestDataFactory.create_user_business_access(
            user_id=viewer_user.id,
            business_id=business.id,
            permission_level="read_only"
        )
        self.db_session.add(viewer_access)
        
        await self.db_session.commit()
        self.created_entities["user_access"].extend([admin_access, viewer_access])
        
        # Create some reviews
        reviews = TestDataFactory.create_review_batch(
            business_id=business.id,
            count=20,
            date_range_days=30
        )
        
        for review in reviews:
            self.db_session.add(review)
        
        await self.db_session.commit()
        
        for review in reviews:
            await self.db_session.refresh(review)
        
        self.created_entities["reviews"].extend(reviews)
        
        # Create classifications
        classifications = TestDataFactory.create_classification_batch(
            [review.id for review in reviews]
        )
        
        for classification in classifications:
            self.db_session.add(classification)
        
        await self.db_session.commit()
        
        for classification in classifications:
            await self.db_session.refresh(classification)
        
        self.created_entities["classifications"].extend(classifications)
        
        logger.info(f"Basic scenario seeded: 1 org, 1 business, 2 users, {len(reviews)} reviews")
        
        return {
            "organization": org,
            "business": business,
            "admin_user": admin_user,
            "viewer_user": viewer_user,
            "reviews": reviews,
            "classifications": classifications
        }
    
    async def seed_multi_tenant_scenario(self) -> Dict[str, Any]:
        """Seed database with multi-tenant scenario (multiple orgs and businesses)."""
        logger.info("Seeding multi-tenant test scenario...")
        
        organizations = []
        all_businesses = []
        all_users = []
        
        # Create 3 organizations
        for i in range(3):
            org = TestDataFactory.create_organization(
                name=f"Organization {i+1}",
                subscription_tier=["basic", "premium", "enterprise"][i]
            )
            self.db_session.add(org)
            organizations.append(org)
        
        await self.db_session.commit()
        
        for org in organizations:
            await self.db_session.refresh(org)
        
        self.created_entities["organizations"].extend(organizations)
        
        # Create businesses and users for each organization
        for i, org in enumerate(organizations):
            # Create 2-3 businesses per organization
            business_count = 2 + (i % 2)  # 2, 3, 2 businesses
            org_businesses = []
            
            for j in range(business_count):
                business = TestDataFactory.create_business(
                    name=f"Restaurant {i+1}-{j+1}",
                    organization_id=org.id
                )
                self.db_session.add(business)
                org_businesses.append(business)
            
            await self.db_session.commit()
            
            for business in org_businesses:
                await self.db_session.refresh(business)
            
            all_businesses.extend(org_businesses)
            self.created_entities["businesses"].extend(org_businesses)
            
            # Create users for this organization
            org_users = []
            
            # Admin user
            admin = TestDataFactory.create_user(
                email=f"admin@org{i+1}.test",
                name=f"Admin User {i+1}",
                role="admin",
                organization_id=org.id
            )
            self.db_session.add(admin)
            org_users.append(admin)
            
            # Viewer users
            for k in range(2):
                viewer = TestDataFactory.create_user(
                    email=f"viewer{k+1}@org{i+1}.test",
                    name=f"Viewer {k+1} Org {i+1}",
                    role="viewer",
                    organization_id=org.id
                )
                self.db_session.add(viewer)
                org_users.append(viewer)
            
            await self.db_session.commit()
            
            for user in org_users:
                await self.db_session.refresh(user)
            
            all_users.extend(org_users)
            self.created_entities["users"].extend(org_users)
            
            # Create user business access
            for user in org_users:
                for business in org_businesses:
                    permission = "full_access" if user.role == "admin" else "read_only"
                    access = TestDataFactory.create_user_business_access(
                        user_id=user.id,
                        business_id=business.id,
                        permission_level=permission
                    )
                    self.db_session.add(access)
                    self.created_entities["user_access"].append(access)
            
            await self.db_session.commit()
        
        logger.info(f"Multi-tenant scenario seeded: {len(organizations)} orgs, {len(all_businesses)} businesses, {len(all_users)} users")
        
        return {
            "organizations": organizations,
            "businesses": all_businesses,
            "users": all_users
        }
    
    async def seed_performance_scenario(self, review_count: int = 1000) -> Dict[str, Any]:
        """Seed database with large dataset for performance testing."""
        logger.info(f"Seeding performance test scenario with {review_count} reviews...")
        
        # Create organization and business
        org = TestDataFactory.create_organization(
            name="Performance Test Organization"
        )
        self.db_session.add(org)
        await self.db_session.commit()
        await self.db_session.refresh(org)
        self.created_entities["organizations"].append(org)
        
        business = TestDataFactory.create_business(
            name="Performance Test Restaurant",
            organization_id=org.id
        )
        self.db_session.add(business)
        await self.db_session.commit()
        await self.db_session.refresh(business)
        self.created_entities["businesses"].append(business)
        
        # Create reviews in batches to avoid memory issues
        batch_size = 100
        all_reviews = []
        
        for i in range(0, review_count, batch_size):
            current_batch_size = min(batch_size, review_count - i)
            reviews = TestDataFactory.create_review_batch(
                business_id=business.id,
                count=current_batch_size,
                date_range_days=365  # Full year of data
            )
            
            for review in reviews:
                self.db_session.add(review)
            
            await self.db_session.commit()
            
            for review in reviews:
                await self.db_session.refresh(review)
            
            all_reviews.extend(reviews)
            self.created_entities["reviews"].extend(reviews)
            
            # Create classifications for this batch
            classifications = TestDataFactory.create_classification_batch(
                [review.id for review in reviews]
            )
            
            for classification in classifications:
                self.db_session.add(classification)
            
            await self.db_session.commit()
            
            for classification in classifications:
                await self.db_session.refresh(classification)
            
            self.created_entities["classifications"].extend(classifications)
            
            logger.info(f"Processed batch {i//batch_size + 1}/{(review_count + batch_size - 1)//batch_size}")
        
        # Create daily analytics for the year
        analytics = []
        for i in range(365):
            analytics_date = datetime.now().date() - timedelta(days=i)
            daily_analytics = TestDataFactory.create_daily_analytics(
                business_id=business.id,
                date=analytics_date
            )
            self.db_session.add(daily_analytics)
            analytics.append(daily_analytics)
        
        await self.db_session.commit()
        
        for analytic in analytics:
            await self.db_session.refresh(analytic)
        
        self.created_entities["analytics"].extend(analytics)
        
        logger.info(f"Performance scenario seeded: {len(all_reviews)} reviews, {len(analytics)} daily analytics")
        
        return {
            "organization": org,
            "business": business,
            "reviews": all_reviews,
            "daily_analytics": analytics,
            "total_reviews": len(all_reviews)
        }
    
    async def seed_conversation_scenario(self) -> Dict[str, Any]:
        """Seed database with conversation and chat history data."""
        logger.info("Seeding conversation test scenario...")
        
        # Use basic scenario as foundation
        basic_data = await self.seed_basic_scenario()
        
        business = basic_data["business"]
        admin_user = basic_data["admin_user"]
        
        # Create multiple conversations
        conversations = []
        all_messages = []
        
        for i in range(3):
            conversation = TestDataFactory.create_conversation(
                business_id=business.id,
                user_id=admin_user.id,
                language="en"
            )
            self.db_session.add(conversation)
            conversations.append(conversation)
        
        await self.db_session.commit()
        
        for conversation in conversations:
            await self.db_session.refresh(conversation)
        
        self.created_entities["conversations"].extend(conversations)
        
        # Create messages for each conversation
        conversation_topics = [
            "How is my restaurant performing this week?",
            "What should I focus on to improve customer satisfaction?",
            "Can you analyze the sentiment trends for this month?"
        ]
        
        for i, conversation in enumerate(conversations):
            # User message
            user_msg = TestDataFactory.create_conversation_message(
                conversation_id=conversation.id,
                role="user",
                content=conversation_topics[i]
            )
            self.db_session.add(user_msg)
            all_messages.append(user_msg)
            
            # Assistant response
            assistant_msg = TestDataFactory.create_conversation_message(
                conversation_id=conversation.id,
                role="assistant",
                content=f"Based on your recent data, here's my analysis for topic {i+1}...",
                ai_model="claude-haiku"
            )
            self.db_session.add(assistant_msg)
            all_messages.append(assistant_msg)
        
        await self.db_session.commit()
        
        for message in all_messages:
            await self.db_session.refresh(message)
        
        self.created_entities["messages"].extend(all_messages)
        
        logger.info(f"Conversation scenario seeded: {len(conversations)} conversations, {len(all_messages)} messages")
        
        return {
            **basic_data,
            "conversations": conversations,
            "messages": all_messages
        }
    
    async def cleanup_all(self):
        """Clean up all created entities from the database."""
        logger.info("Cleaning up seeded test data...")
        
        # Delete in reverse order of dependencies
        entity_types = [
            ("messages", ConversationMessage),
            ("conversations", Conversation),
            ("ai_logs", AIUsageLog),
            ("analytics", DailyAnalytics),
            ("classifications", Classification),
            ("reviews", Review),
            ("user_access", UserBusinessAccess),
            ("users", User),
            ("businesses", Business),
            ("organizations", Organization)
        ]
        
        for entity_name, model_class in entity_types:
            entities = self.created_entities.get(entity_name, [])
            if entities:
                # Delete by IDs to avoid stale object issues
                entity_ids = [entity.id for entity in entities]
                await self.db_session.execute(
                    delete(model_class).where(model_class.id.in_(entity_ids))
                )
                await self.db_session.commit()
                logger.info(f"Cleaned up {len(entities)} {entity_name}")
        
        # Clear tracking
        self.created_entities = {key: [] for key in self.created_entities.keys()}
        
        logger.info("Cleanup completed")
    
    async def verify_data_integrity(self) -> Dict[str, bool]:
        """Verify the integrity of seeded data."""
        logger.info("Verifying data integrity...")
        
        results = {}
        
        # Check organizations exist
        org_count = len(await self.db_session.execute(select(Organization)).fetchall())
        results["organizations_exist"] = org_count > 0
        
        # Check businesses have organizations
        businesses = await self.db_session.execute(select(Business)).fetchall()
        results["businesses_have_orgs"] = all(
            business[0].organization_id is not None for business in businesses
        )
        
        # Check reviews have businesses
        reviews = await self.db_session.execute(select(Review)).fetchall()
        results["reviews_have_businesses"] = all(
            review[0].business_id is not None for review in reviews
        )
        
        # Check classifications have reviews
        classifications = await self.db_session.execute(select(Classification)).fetchall()
        results["classifications_have_reviews"] = all(
            classification[0].review_id is not None for classification in classifications
        )
        
        logger.info(f"Data integrity check: {results}")
        return results


class SeedingPresets:
    """Predefined seeding presets for common test scenarios."""
    
    @staticmethod
    async def minimal_dataset(db_session: AsyncSession) -> Dict[str, Any]:
        """Create minimal dataset for unit tests."""
        seeder = DatabaseSeeder(db_session)
        return await seeder.seed_basic_scenario()
    
    @staticmethod
    async def integration_dataset(db_session: AsyncSession) -> Dict[str, Any]:
        """Create comprehensive dataset for integration tests."""
        seeder = DatabaseSeeder(db_session)
        return await seeder.seed_multi_tenant_scenario()
    
    @staticmethod
    async def performance_dataset(db_session: AsyncSession, review_count: int = 500) -> Dict[str, Any]:
        """Create large dataset for performance tests."""
        seeder = DatabaseSeeder(db_session)
        return await seeder.seed_performance_scenario(review_count)
    
    @staticmethod
    async def e2e_dataset(db_session: AsyncSession) -> Dict[str, Any]:
        """Create complete dataset for E2E tests."""
        seeder = DatabaseSeeder(db_session)
        
        # Combine multiple scenarios
        multi_tenant_data = await seeder.seed_multi_tenant_scenario()
        conversation_data = await seeder.seed_conversation_scenario()
        
        return {
            **multi_tenant_data,
            "conversations": conversation_data["conversations"],
            "messages": conversation_data["messages"]
        }