"""
Base repository implementation with common CRUD operations.

This module provides the abstract base repository class and common
database operations that can be inherited by specific repositories.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict, Union
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Type variables for generic repository
ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class NotFoundError(RepositoryError):
    """Raised when a requested resource is not found."""
    pass


class DuplicateError(RepositoryError):
    """Raised when trying to create a duplicate resource."""
    pass


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """Abstract base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """Initialize repository with model and database session.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record.

        Args:
            obj_in: Pydantic schema with creation data

        Returns:
            Created model instance
            
        Raises:
            DuplicateError: If record violates unique constraints
            RepositoryError: For other database errors
        """
        try:
            obj_data = obj_in.model_dump()
            db_obj = self.model(**obj_data)
            self.session.add(db_obj)
            await self.session.commit()
            await self.session.refresh(db_obj)
            logger.debug(f"Created {self.model.__name__} with ID: {db_obj.id}")
            return db_obj
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            raise DuplicateError(f"Record already exists: {str(e)}")
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error creating {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to create record: {str(e)}")

    async def get(self, id: UUID) -> Optional[ModelType]:
        """Get a record by ID.

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting {self.model.__name__} {id}: {e}")
            raise RepositoryError(f"Failed to get record: {str(e)}")

    async def get_or_raise(self, id: UUID) -> ModelType:
        """Get a record by ID or raise NotFoundError.

        Args:
            id: Record UUID

        Returns:
            Model instance
            
        Raises:
            NotFoundError: If record not found
        """
        obj = await self.get(id)
        if not obj:
            raise NotFoundError(f"{self.model.__name__} with ID {id} not found")
        return obj

    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        order_by: Optional[str] = None,
        **filters
    ) -> List[ModelType]:
        """Get multiple records with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field name to order by (prefix with '-' for descending)
            **filters: Additional filter conditions

        Returns:
            List of model instances
        """
        try:
            query = select(self.model)

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)

            # Apply ordering
            if order_by:
                if order_by.startswith('-'):
                    field_name = order_by[1:]
                    if hasattr(self.model, field_name):
                        query = query.order_by(getattr(self.model, field_name).desc())
                else:
                    if hasattr(self.model, order_by):
                        query = query.order_by(getattr(self.model, order_by))

            query = query.offset(skip).limit(limit)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Database error getting multiple {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to get records: {str(e)}")

    async def update(self, id: UUID, obj_in: UpdateSchemaType) -> Optional[ModelType]:
        """Update a record by ID.

        Args:
            id: Record UUID
            obj_in: Pydantic schema with update data

        Returns:
            Updated model instance or None if not found
            
        Raises:
            RepositoryError: For database errors
        """
        try:
            # Get existing record
            db_obj = await self.get(id)
            if not db_obj:
                return None

            # Update fields
            update_data = obj_in.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            await self.session.commit()
            await self.session.refresh(db_obj)
            logger.debug(f"Updated {self.model.__name__} with ID: {id}")
            return db_obj
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error updating {self.model.__name__} {id}: {e}")
            raise RepositoryError(f"Failed to update record: {str(e)}")

    async def delete(self, id: UUID) -> bool:
        """Delete a record by ID.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found
            
        Raises:
            RepositoryError: For database errors
        """
        try:
            result = await self.session.execute(
                delete(self.model).where(self.model.id == id)
            )
            await self.session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.debug(f"Deleted {self.model.__name__} with ID: {id}")
            return deleted
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error deleting {self.model.__name__} {id}: {e}")
            raise RepositoryError(f"Failed to delete record: {str(e)}")

    async def count(self, **filters) -> int:
        """Count records with optional filtering.

        Args:
            **filters: Filter conditions

        Returns:
            Number of matching records
        """
        try:
            query = select(func.count(self.model.id))

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)

            result = await self.session.execute(query)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Database error counting {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to count records: {str(e)}")

    async def exists(self, id: UUID) -> bool:
        """Check if a record exists by ID.

        Args:
            id: Record UUID

        Returns:
            True if exists, False otherwise
        """
        try:
            result = await self.session.execute(
                select(self.model.id).where(self.model.id == id)
            )
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error checking existence of {self.model.__name__} {id}: {e}")
            raise RepositoryError(f"Failed to check record existence: {str(e)}")

    async def bulk_create(self, objects: List[CreateSchemaType]) -> List[ModelType]:
        """Create multiple records in a single transaction.

        Args:
            objects: List of Pydantic schemas with creation data

        Returns:
            List of created model instances
            
        Raises:
            RepositoryError: For database errors
        """
        try:
            db_objects = []
            for obj_in in objects:
                obj_data = obj_in.model_dump()
                db_obj = self.model(**obj_data)
                db_objects.append(db_obj)
                self.session.add(db_obj)

            await self.session.commit()
            
            # Refresh all objects
            for db_obj in db_objects:
                await self.session.refresh(db_obj)
            
            logger.debug(f"Bulk created {len(db_objects)} {self.model.__name__} records")
            return db_objects
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error bulk creating {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to bulk create records: {str(e)}")

    async def find_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """Find a single record by a specific field value.

        Args:
            field_name: Name of the field to search by
            value: Value to search for

        Returns:
            Model instance or None if not found
        """
        try:
            if not hasattr(self.model, field_name):
                raise ValueError(f"Field {field_name} does not exist on {self.model.__name__}")
            
            result = await self.session.execute(
                select(self.model).where(getattr(self.model, field_name) == value)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error finding {self.model.__name__} by {field_name}: {e}")
            raise RepositoryError(f"Failed to find record: {str(e)}")