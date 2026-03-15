"""
UserSetting model for per-user key/value configuration.

Unlike other models, UserSetting does not inherit from BaseModel — it has no
UUID id and no client_id. Its primary key is the composite (user_id, key),
meaning each user has their own independent set of settings.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, String, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.extensions import db


class UserSetting(db.Model):
    """
    Per-user key/value store for application settings.

    Primary key is (user_id, key), so each user maintains independent settings.
    Values use JSONB for flexible structured storage without schema changes.

    Attributes:
        user_id: FK to users.id. Part of composite PK. CASCADE DELETE on user removal.
        key: Setting identifier (e.g. 'primary_currency'). Part of composite PK.
        value: JSONB setting value.
        updated_at: Auto-updated modification timestamp.
    """

    __tablename__ = "user_settings"
    __allow_unmapped__ = True

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    key = Column(String(100), nullable=False)
    value = Column(JSONB, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "key", name="pk_user_settings"),
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model to dictionary.

        Returns:
            Dict with user_id (str), key, value, and updated_at (ISO).
        """
        return {
            "user_id": str(self.user_id),
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"<UserSetting user={self.user_id} {self.key}={self.value!r}>"
