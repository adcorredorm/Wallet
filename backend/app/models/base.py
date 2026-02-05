"""
Base model with common fields and utilities.

All models inherit from BaseModel to ensure consistent timestamps and IDs.
"""

from datetime import datetime
from uuid import uuid4
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class BaseModel(db.Model):
    """
    Base model with common fields for all entities.

    Provides:
    - UUID primary key
    - created_at timestamp
    - updated_at timestamp (auto-updated on modification)
    - to_dict() method for serialization
    """

    __abstract__ = True
    __allow_unmapped__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model to dictionary representation.

        Returns:
            Dictionary with all column names and values
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__} {self.id}>"
