"""
Account Pydantic schemas for validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class AccountType(str, Enum):
    """Account type enumeration."""

    DEBIT = "debit"
    CREDIT = "credit"
    CASH = "cash"


# Bootstrap fallback: used when the exchange_rates table is empty or unreachable.
# Should match frontend constants (src/utils/constants.ts).
SUPPORTED_CURRENCIES = {"COP", "USD", "EUR", "BRL", "JPY", "BTC", "ETH", "ARS", "GBP"}


def _get_supported_currencies() -> set[str]:
    """Return the set of valid currency codes.

    Queries the ``exchange_rates`` table for all known currency codes. Falls
    back to the hardcoded ``SUPPORTED_CURRENCIES`` bootstrap set when:

    - The table is empty (no rates seeded yet).
    - The query raises any exception (DB unreachable, table not yet created,
      no application context, etc.).

    The fallback is always silent — callers are never aware of whether the
    live table or the static set was used.

    Returns:
        A set of upper-case currency code strings suitable for membership
        testing inside Pydantic field validators.
    """
    try:
        from app.models.exchange_rate import ExchangeRate

        codes = {
            row.currency_code
            for row in ExchangeRate.query.with_entities(
                ExchangeRate.currency_code
            ).all()
        }
        return codes if codes else SUPPORTED_CURRENCIES
    except Exception:
        return SUPPORTED_CURRENCIES


class AccountCreate(BaseModel):
    """
    Schema for creating a new account.

    Args:
        name: Account name (1-100 characters)
        type: Account type (debit, credit, cash)
        currency: Currency code (ISO 4217, 3 characters)
        description: Optional description (max 500 characters)
        tags: List of tags (max 10, each max 50 characters)
        offline_id: Optional client-generated UUID for offline idempotency.
            When provided, a retry of the same creation request will return
            the existing record instead of creating a duplicate.
    """

    name: str = Field(..., min_length=1, max_length=100)
    type: AccountType
    currency: str = Field(..., min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    offline_id: Optional[str] = Field(None, max_length=100)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate that currency is supported.

        The set of valid currencies is resolved at validation time by querying
        the ``exchange_rates`` table, falling back to ``SUPPORTED_CURRENCIES``
        when the table is empty or the DB is unreachable.
        """
        if not v:
            raise ValueError("Divisa es requerida")
        v = v.upper()
        supported = _get_supported_currencies()
        if v not in supported:
            raise ValueError(
                f"Divisa no soportada. Opciones válidas: {', '.join(sorted(supported))}"
            )
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate and truncate tags."""
        if len(v) > 10:
            raise ValueError("Maximo 10 tags permitidos")
        return [tag[:50] for tag in v]


class AccountUpdate(BaseModel):
    """
    Schema for updating an existing account.

    All fields are optional to support partial updates.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[AccountType] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None
    active: Optional[bool] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        """Validate that currency is supported if provided.

        The set of valid currencies is resolved at validation time by querying
        the ``exchange_rates`` table, falling back to ``SUPPORTED_CURRENCIES``
        when the table is empty or the DB is unreachable.
        """
        if v is None:
            return v
        v = v.upper()
        supported = _get_supported_currencies()
        if v not in supported:
            raise ValueError(
                f"Divisa no soportada. Opciones: {', '.join(sorted(supported))}"
            )
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate and truncate tags if provided."""
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximo 10 tags permitidos")
        return [tag[:50] for tag in v]


class AccountResponse(BaseModel):
    """
    Schema for account responses.

    Returns:
        Complete account information including metadata
    """

    id: UUID
    name: str
    type: AccountType
    currency: str
    description: Optional[str]
    tags: list[str]
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
