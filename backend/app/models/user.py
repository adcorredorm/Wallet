"""
User model for authenticated users.

Users authenticate via Google OAuth only. No passwords are stored.
Each user owns their financial data (accounts, transactions, etc.)
through a foreign key on every domain model.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from app.extensions import db


class User(db.Model):
    """
    Authenticated user record.

    Created on first Google OAuth login. The google_id is the 'sub' claim
    from the Google id_token and is the canonical identity key.

    Attributes:
        id: UUID primary key generated server-side.
        google_id: Google account subject identifier ('sub' from id_token). Unique.
        email: User's Google email address. Unique.
        name: User's display name from Google profile.
        created_at: UTC timestamp of account creation.
        updated_at: UTC timestamp of last profile update.
    """

    __tablename__ = "users"
    __allow_unmapped__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_users_google_id", "google_id"),
        Index("idx_users_email", "email"),
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize user to dictionary.

        Returns:
            Dict with id (str), email, name, created_at (ISO), updated_at (ISO).
        """
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"<User {self.email}>"
