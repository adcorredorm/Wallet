"""
UserSetting repository for per-user key/value database operations.

UserSetting uses a composite primary key (user_id, key) rather than a UUID,
so it does not extend BaseRepository. The set() method is a full upsert.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

from app.extensions import db
from app.models.user_setting import UserSetting


class SettingsRepository:
    """
    Repository for UserSetting with per-user isolation.

    All methods require a user_id to scope operations to a single user's
    settings. No cross-user reads are possible through this interface.
    """

    def get(self, user_id: UUID, key: str) -> Optional[UserSetting]:
        """
        Retrieve a single setting by user and key.

        Args:
            user_id: Owning user's UUID.
            key: Setting identifier (e.g. 'primary_currency').

        Returns:
            UserSetting instance if the key exists for this user, else None.
        """
        return db.session.execute(
            db.select(UserSetting).where(
                UserSetting.user_id == user_id,
                UserSetting.key == key,
            )
        ).scalars().one_or_none()

    def get_all(self, user_id: UUID) -> list[UserSetting]:
        """
        Retrieve all settings for a user.

        Args:
            user_id: Owning user's UUID.

        Returns:
            List of UserSetting instances for this user.
        """
        return (
            db.session.execute(
                db.select(UserSetting).where(UserSetting.user_id == user_id)
            )
            .scalars()
            .all()
        )

    def set(self, user_id: UUID, key: str, value: Any) -> UserSetting:
        """
        Insert or update a setting for the given user and key.

        Uses PostgreSQL INSERT … ON CONFLICT (user_id, key) DO UPDATE.

        Args:
            user_id: Owning user's UUID.
            key: Setting identifier.
            value: Python value stored as JSONB.

        Returns:
            The persisted UserSetting instance, refreshed from the database.
        """
        now = datetime.utcnow()
        stmt = (
            insert(UserSetting)
            .values(
                user_id=user_id,
                key=key,
                value=value,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "key"],
                set_={
                    "value": value,
                    "updated_at": now,
                },
            )
        )
        db.session.execute(stmt)
        db.session.commit()
        return self.get(user_id, key)  # type: ignore[return-value]
