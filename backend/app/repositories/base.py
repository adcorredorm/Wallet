"""
Base repository with common CRUD operations.
"""

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

    def get_all(self) -> list[T]:
        """
        Get all records.

        Returns:
            List of all model instances
        """
        return db.session.execute(db.select(self.model)).scalars().all()

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
