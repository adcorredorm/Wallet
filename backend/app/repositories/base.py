"""
Base repository with common CRUD operations.
"""

from datetime import datetime
from typing import TypeVar, Generic, Optional, Type
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.base import BaseModel
from app.utils.exceptions import NotFoundError

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """
    Generic base repository with common CRUD operations.

    Provides standard create, read, update, delete operations that can be
    inherited by specific repositories.
    """

    def __init__(self, model: Type[T]):
        """
        Initialize repository with model class.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model

    def get_by_id(self, id: UUID) -> Optional[T]:
        """
        Get a single record by ID.

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        return db.session.get(self.model, id)

    def get_by_client_id(self, client_id: str) -> Optional[T]:
        """
        Get a single record by its client-generated idempotency key.

        This method supports the offline-first pattern: when a client retries
        a creation request after an uncertain response, it sends the same
        client_id so the server can detect the duplicate and return the
        previously persisted record rather than creating a second one.

        Args:
            client_id: Client-generated idempotency key (max 100 characters)

        Returns:
            Model instance if a record with that client_id exists, else None
        """
        return (
            db.session.execute(
                db.select(self.model).where(self.model.client_id == client_id)
            )
            .scalars()
            .one_or_none()
        )

    def get_by_id_or_fail(self, id: UUID) -> T:
        """
        Get a single record by ID or raise exception.

        Args:
            id: Record UUID

        Returns:
            Model instance

        Raises:
            NotFoundError: If record not found
        """
        record = self.get_by_id(id)
        if not record:
            raise NotFoundError(self.model.__name__, str(id))
        return record

    def get_all(self, updated_since: datetime | None = None) -> list[T]:
        """
        Get all records, optionally filtered by modification time.

        Args:
            updated_since: Only return records with updated_at >= updated_since
                (naive UTC). None returns all records.

        Returns:
            List of model instances
        """
        query = db.select(self.model)
        if updated_since is not None:
            query = query.where(self.model.updated_at >= updated_since)
        return db.session.execute(query).scalars().all()

    def create(self, **kwargs) -> T:
        """
        Create a new record.

        Args:
            **kwargs: Field values for the new record

        Returns:
            Created model instance

        Raises:
            IntegrityError: If database constraints are violated
        """
        instance = self.model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        db.session.refresh(instance)
        return instance

    def update(self, instance: T, **kwargs) -> T:
        """
        Update an existing record.

        Args:
            instance: Model instance to update
            **kwargs: Fields to update

        Returns:
            Updated model instance
        """
        for key, value in kwargs.items():
            if value is not None:  # Only update non-None values
                setattr(instance, key, value)

        db.session.commit()
        db.session.refresh(instance)
        return instance

    def delete(self, instance: T) -> None:
        """
        Delete a record.

        Args:
            instance: Model instance to delete
        """
        db.session.delete(instance)
        db.session.commit()

    def count(self) -> int:
        """
        Count total records.

        Returns:
            Total number of records
        """
        return db.session.query(self.model).count()
