"""
Account Pydantic schemas for validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from enum import Enum


class AccountType(str, Enum):
    """Account type enumeration."""

    DEBIT = "debit"
    CREDIT = "credit"
    CASH = "cash"


# Supported currencies (ISO 4217)
# Should match frontend constants (src/utils/constants.ts)
SUPPORTED_CURRENCIES = {"EUR", "USD", "GBP", "COP"}


class AccountCreate(BaseModel):
    """
    Schema for creating a new account.

    Args:
        name: Account name (1-100 characters)
        type: Account type (debit, credit, cash)
        currency: Currency code (ISO 4217, 3 characters)
        description: Optional description (max 500 characters)
        tags: List of tags (max 10, each max 50 characters)
        client_id: Optional client-generated UUID for offline idempotency.
            When provided, a retry of the same creation request will return
            the existing record instead of creating a duplicate.
    """

    name: str = Field(..., min_length=1, max_length=100)
    type: AccountType
    currency: str = Field(..., min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    client_id: Optional[str] = Field(None, max_length=100)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate that currency is supported."""
        if not v:
            raise ValueError("Divisa es requerida")
        v = v.upper()
        if v not in SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Divisa no soportada. Opciones válidas: {', '.join(sorted(SUPPORTED_CURRENCIES))}"
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
        """Validate that currency is supported if provided."""
        if v is None:
            return v
        v = v.upper()
        if v not in SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Divisa no soportada. Opciones: {', '.join(sorted(SUPPORTED_CURRENCIES))}"
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


class AccountWithBalance(AccountResponse):
    """
    Schema for account with calculated balance.

    Extends AccountResponse with dynamically calculated balance.
    Balance is never stored in the database.
    """

    balance: Decimal = Field(..., description="Calculated account balance")
