"""
UserSetting service containing business logic for application settings.

Known keys and their validation rules
--------------------------------------
``primary_currency``
    Must be a string matching the regex ``/^[A-Z]{2,10}$/``.

Any key not in the known set raises ``ValidationError`` to prevent accidental
writes of unsupported configuration.
"""

import re
from typing import Any

from app.models.user_setting import UserSetting
from app.repositories.user_setting import SettingsRepository
from app.utils.exceptions import ValidationError

# Registry of known setting keys mapped to their validator functions.
# Each validator receives the raw value and either returns the (possibly
# coerced) value or raises ValidationError.
_CURRENCY_RE = re.compile(r"^[A-Z]{2,10}$")

_KNOWN_KEYS: dict[str, Any] = {
    "primary_currency": None,  # sentinel — validated inline below
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
    """Service for application settings business logic."""

    def __init__(self) -> None:
        """Initialise service with its repository."""
        self.repository = SettingsRepository()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any:
        """
        Return the Python value stored for the given key.

        The value is retrieved directly from the JSONB column, so for a
        currency string like ``"COP"`` the returned Python object is the
        string ``'COP'``.

        Args:
            key: Setting identifier (e.g. ``'primary_currency'``).

        Returns:
            The stored Python value, or None if the key does not exist.
        """
        row = self.repository.get(key)
        if row is None:
            return None
        return row.value

    def get_all(self) -> dict[str, Any]:
        """
        Return all settings as a flat ``{key: value}`` dictionary.

        Returns:
            Dictionary mapping every stored setting key to its Python value.
        """
        from app.extensions import db
        from app.models.user_setting import UserSetting as _US

        all_rows = db.session.execute(db.select(_US)).scalars().all()
        return {row.key: row.value for row in all_rows}

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any) -> UserSetting:
        """
        Persist a setting after validating both key and value.

        Args:
            key: Setting identifier. Must be one of the known keys.
            value: New value. Validated according to per-key rules.

        Returns:
            Persisted UserSetting instance.

        Raises:
            ValidationError: If ``key`` is unknown or ``value`` fails
                per-key validation.
        """
        if key not in _KNOWN_KEYS:
            raise ValidationError(
                f"Clave de configuración desconocida: '{key}'. "
                f"Claves válidas: {', '.join(sorted(_KNOWN_KEYS))}"
            )

        validator = _VALIDATORS.get(key)
        if validator is not None:
            value = validator(value)

        return self.repository.set(key=key, value=value)

