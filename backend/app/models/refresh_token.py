"""
RefreshToken model for managing long-lived session tokens.

At most one active refresh token exists per user. On rotation, the old
token row is deleted and a new one is inserted — there is no revoked_at
column. Token values are never stored in plain text; only the SHA-256
hash is persisted.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from app.extensions import db


class RefreshToken(db.Model):
    """
    Hashed refresh token linked to a user.

    Tokens are physically deleted on rotation (no revoked_at field).
    Only the SHA-256 hex digest is stored — the raw token value is never
    persisted and is transmitted to the client exactly once on issuance.

    Attributes:
        id: UUID primary key.
        user_id: FK to users.id — CASCADE DELETE ensures cleanup.
        token_hash: SHA-256 hex digest of the opaque token string.
        expires_at: UTC expiration timestamp (90 days from issuance).
        created_at: UTC issuance timestamp.
    """

    __tablename__ = "refresh_tokens"
    __allow_unmapped__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_refresh_tokens_token_hash", "token_hash"),
        Index("idx_refresh_tokens_user_id", "user_id"),
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to dictionary (never exposes token_hash).

        Returns:
            Dict with id (str), user_id (str), expires_at (ISO), created_at (ISO).
        """
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        """String representation (uses first 8 chars of hash for readability)."""
        return f"<RefreshToken hash={self.token_hash[:8]}...>"
