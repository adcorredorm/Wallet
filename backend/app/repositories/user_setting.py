"""
UserSetting repository for database operations.

UserSetting uses a string primary key (``key``) rather than a UUID, so it does
not extend BaseRepository.  The set() method is a full upsert: it inserts a new
row or replaces the value of an existing one.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.dialects.postgresql import insert

from app.extensions import db
from app.models.user_setting import UserSetting


class SettingsRepository:
    """Repository for UserSetting entity operations.

    Provides simple key/value access to the ``user_settings`` table.
    All keys are validated at the service layer; this repository is
    intentionally free of business-rule knowledge.
    """

    def get(self, key: str) -> Optional[UserSetting]:
        """
        Retrieve a single setting by its key.

        Args:
            key: Setting identifier (e.g. ``'primary_currency'``).

        Returns:
            UserSetting instance if the key exists, otherwise None.
        """
        return db.session.get(UserSetting, key)

    def set(self, key: str, value: Any) -> UserSetting:
        """
        Insert or update a setting row for the given key.

        Uses PostgreSQL ``INSERT … ON CONFLICT (key) DO UPDATE`` so the
        operation is idempotent and safe under concurrent writes.

        Args:
            key: Setting identifier (primary key).
            value: Python value that will be stored as JSONB. May be a string,
                number, list, dict, or None — anything JSON-serialisable.

        Returns:
            The persisted UserSetting instance, refreshed from the database.
        """
        stmt = (
            insert(UserSetting)
            .values(
                key=key,
                value=value,
                updated_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=["key"],
                set_={
                    "value": value,
                    "updated_at": datetime.utcnow(),
                },
            )
        )

        db.session.execute(stmt)
        db.session.commit()

        row = self.get(key)
        return row  # type: ignore[return-value]  # always present after upsert
