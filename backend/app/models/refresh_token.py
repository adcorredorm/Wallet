"""
RefreshToken model for managing long-lived session tokens.

At most one active refresh token exists per user at a time. On rotation,
the old token's `superseded_at` is set to utcnow() — it remains valid
for a 2-minute grace window to survive network failures. After the grace
period expires it is deleted on the next issuance. Token values are never
stored in plain text; only the SHA-256 hash is persisted.
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

    On rotation, tokens are soft-deleted via `superseded_at` rather than
    physically deleted. A superseded token is still accepted for
    REFRESH_TOKEN_GRACE_SECONDS seconds, allowing the client to recover
    from lost network responses. After the grace period, the token is
    cleaned up on the next issuance.

    Only the SHA-256 hex digest is stored — the raw token value is never
    persisted and is transmitted to the client exactly once on issuance.

    Attributes:
        id: UUID primary key.
        user_id: FK to users.id — CASCADE DELETE ensures cleanup.
        token_hash: SHA-256 hex digest of the opaque token string.
        expires_at: UTC expiration timestamp (90 days from issuance).
        created_at: UTC issuance timestamp.
        superseded_at: UTC timestamp when this token was rotated out.
            None means the token is the current active token.
            Non-None means it is in grace period (or grace has expired).
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
    superseded_at = Column(DateTime, nullable=True, default=None)

    __table_args__ = (
        Index("idx_refresh_tokens_token_hash", "token_hash"),
        Index("idx_refresh_tokens_user_id", "user_id"),
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to dictionary (never exposes token_hash).

        Returns:
            Dict with id (str), user_id (str), expires_at (ISO),
            created_at (ISO), superseded_at (ISO or None).
        """
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "superseded_at": self.superseded_at.isoformat() if self.superseded_at else None,
        }

    def __repr__(self) -> str:
        """String representation (uses first 8 chars of hash for readability)."""
        superseded = f" superseded={self.superseded_at.isoformat()}" if self.superseded_at else ""
        return f"<RefreshToken hash={self.token_hash[:8]}...{superseded}>"
