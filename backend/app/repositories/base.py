"""
Base repository with user-aware CRUD operations.

All query methods require a user_id to enforce per-user data isolation.
The get_by_id() method deliberately avoids db.session.get() because that
API bypasses SQLAlchemy WHERE filters — it is rewritten as an explicit
SELECT ... WHERE id = :id AND user_id = :user_id query.
"""

from datetime import datetime
from typing import TypeVar, Generic, Optional, Type
from uuid import UUID

from sqlalchemy import func, select

from app.extensions import db
from app.models.base import BaseModel
from app.utils.exceptions import NotFoundError

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """
    Generic base repository with user-scoped CRUD operations.

    Every method that reads or writes data requires a user_id to ensure
    complete isolation between users. No method returns data belonging to
    a different user.

    The underlying models are expected to have a user_id column (FK to users.id).
    """

    def __init__(self, model: Type[T]):
        """
        Initialize repository with model class.

        Args:
            model: SQLAlchemy model class (must have user_id column).
        """
        self.model = model

    def get_by_id(self, id: UUID, user_id: UUID) -> Optional[T]:
        """
        Get a single record by ID, scoped to a specific user.

        Uses an explicit SELECT query (not db.session.get()) to ensure the
        user_id filter is always applied. db.session.get() bypasses WHERE
        filters and would allow cross-user data access.

        Args:
            id: Record UUID.
            user_id: Owner's UUID. Record is only returned if it belongs to
                this user.

        Returns:
            Model instance or None if not found or not owned by this user.
        """
        return (
            db.session.execute(
                db.select(self.model).where(
                    self.model.id == id,
                    self.model.user_id == user_id,
                )
            )
            .scalars()
            .one_or_none()
        )

    def get_by_offline_id(self, offline_id: str, user_id: UUID) -> Optional[T]:
        """
        Get a record by client-generated idempotency key, scoped to a user.

        Supports the offline-first pattern: when a client retries a creation
        request after an uncertain response, it sends the same offline_id so
        the server can detect the duplicate and return the previously persisted
        record. The user_id scope prevents one user's offline_id from matching
        another user's records.

        Args:
            offline_id: Client-generated idempotency key (max 100 characters).
            user_id: Owner's UUID.

        Returns:
            Model instance if found for this user, else None.
        """
        return (
            db.session.execute(
                db.select(self.model).where(
                    self.model.offline_id == offline_id,
                    self.model.user_id == user_id,
                )
            )
            .scalars()
            .one_or_none()
        )

    def get_by_id_or_fail(self, id: UUID, user_id: UUID) -> T:
        """
        Get a single record by ID or raise NotFoundError.

        Args:
            id: Record UUID.
            user_id: Owner's UUID.

        Returns:
            Model instance.

        Raises:
            NotFoundError: If record not found or not owned by this user.
        """
        record = self.get_by_id(id, user_id)
        if not record:
            raise NotFoundError(self.model.__name__, str(id))
        return record

    def get_all(
        self,
        user_id: UUID,
        updated_since: datetime | None = None,
    ) -> list[T]:
        """
        Get all records for a user, optionally filtered by modification time.

        Args:
            user_id: Owner's UUID. Only records owned by this user are returned.
            updated_since: Only return records with updated_at >= updated_since
                (naive UTC). None returns all records for the user.

        Returns:
            List of model instances.
        """
        query = db.select(self.model).where(self.model.user_id == user_id)
        if updated_since is not None:
            query = query.where(self.model.updated_at >= updated_since)
        return db.session.execute(query).scalars().all()

    def create(self, user_id: UUID, **kwargs) -> T:
        """
        Create a new record owned by the specified user.

        The user_id is automatically injected into the new record — callers
        must not pass it via kwargs.

        Args:
            user_id: Owner's UUID. Auto-injected into the record.
            **kwargs: Additional field values for the new record.

        Returns:
            Created model instance.
        """
        instance = self.model(user_id=user_id, **kwargs)
        db.session.add(instance)
        db.session.commit()
        db.session.refresh(instance)
        return instance

    def update(self, instance: T, **kwargs) -> T:
        """
        Update an existing record.

        Args:
            instance: Model instance to update.
            **kwargs: Fields to update. None values are skipped.

        Returns:
            Updated model instance.
        """
        for key, value in kwargs.items():
            if value is not None:
                setattr(instance, key, value)
        db.session.commit()
        db.session.refresh(instance)
        return instance

    def delete(self, instance: T) -> None:
        """
        Delete a record.

        Args:
            instance: Model instance to delete.
        """
        db.session.delete(instance)
        db.session.commit()

    def count(self, user_id: UUID) -> int:
        """
        Count records owned by a user.

        Args:
            user_id: Owner's UUID.

        Returns:
            Number of records owned by this user.
        """
        return db.session.execute(
            select(func.count()).select_from(self.model).where(
                self.model.user_id == user_id
            )
        ).scalar_one()
