"""
UserSetting model for storing application-level key/value configuration.

Unlike other models, UserSetting does not inherit from BaseModel — it has no
UUID id and no client_id, because settings are global singletons identified
by their key string (e.g. 'primary_currency').
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class UserSetting(db.Model):
    """
    Key/value store for user-level application settings.

    Each row represents a single setting identified by its key. The value
    column uses JSONB to allow structured data (strings, numbers, objects,
    arrays) without requiring a schema change for each new setting type.

    Attributes:
        key: Setting identifier (primary key), e.g. 'primary_currency'.
        value: Setting value stored as JSONB. For a currency string this would
            be the JSON string ``"COP"`` (including quotes), not the bare word.
        updated_at: Timestamp auto-updated whenever the row is written.
    """

    __tablename__ = "user_settings"
    __allow_unmapped__ = True

    key = Column(String(100), primary_key=True, nullable=False)
    value = Column(JSONB, nullable=False)
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
            Dictionary with key, value, and updated_at fields.
        """
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at,
        }

    def __repr__(self) -> str:
        """String representation of the user setting."""
        return f"<UserSetting {self.key}={self.value!r}>"
