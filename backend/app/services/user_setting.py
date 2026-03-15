"""
UserSetting service containing business logic for per-user application settings.

Known keys and their validation rules
---------------------------------------
``primary_currency``
    Must be a string matching the regex ``/^[A-Z]{2,10}$/``.

Any key not in the known set raises ``ValidationError``.
"""

import re
from typing import Any
from uuid import UUID

from app.models.user_setting import UserSetting
from app.repositories.user_setting import SettingsRepository
from app.utils.exceptions import ValidationError

_CURRENCY_RE = re.compile(r"^[A-Z]{2,10}$")
_KNOWN_KEYS: dict[str, Any] = {
    "primary_currency": None,
}


def _validate_primary_currency(value: Any) -> str:
    """
    Validate the ``primary_currency`` setting value.

    Args:
        value: Candidate value from the caller.

    Returns:
        Uppercased currency code string.

    Raises:
        ValidationError: If the value is not a non-empty string of 2-10
            uppercase ASCII letters.
    """
    if not isinstance(value, str):
        raise ValidationError(
            "primary_currency debe ser una cadena de texto (ej. 'USD', 'COP')"
        )
    upper = value.upper()
    if not _CURRENCY_RE.match(upper):
        raise ValidationError(
            "primary_currency debe ser un código de divisa de 2 a 10 letras mayúsculas "
            "(ej. 'USD', 'COP', 'BTC')"
        )
    return upper


_VALIDATORS = {
    "primary_currency": _validate_primary_currency,
}


class SettingsService:
    """Service for per-user application settings business logic."""

    def __init__(self) -> None:
        """Initialise service with its repository."""
        self.repository = SettingsRepository()

    def get(self, user_id: UUID, key: str) -> Any:
        """
        Return the Python value stored for the given user and key.

        Args:
            user_id: Owning user's UUID.
            key: Setting identifier (e.g. 'primary_currency').

        Returns:
            The stored Python value, or None if the key does not exist.
        """
        row = self.repository.get(user_id, key)
        if row is None:
            return None
        return row.value

    def get_all(self, user_id: UUID) -> dict[str, Any]:
        """
        Return all settings for a user as a flat ``{key: value}`` dictionary.

        Args:
            user_id: Owning user's UUID.

        Returns:
            Dictionary mapping every stored setting key to its Python value.
        """
        rows = self.repository.get_all(user_id)
        return {row.key: row.value for row in rows}

    def set(self, user_id: UUID, key: str, value: Any) -> UserSetting:
        """
        Persist a setting after validating both key and value.

        Args:
            user_id: Owning user's UUID.
            key: Setting identifier. Must be one of the known keys.
            value: New value. Validated according to per-key rules.

        Returns:
            Persisted UserSetting instance.

        Raises:
            ValidationError: If key is unknown or value fails per-key validation.
        """
        if key not in _KNOWN_KEYS:
            raise ValidationError(
                f"Clave de configuración desconocida: '{key}'. "
                f"Claves válidas: {', '.join(sorted(_KNOWN_KEYS))}"
            )
        validator = _VALIDATORS.get(key)
        if validator is not None:
            value = validator(value)
        return self.repository.set(user_id=user_id, key=key, value=value)
