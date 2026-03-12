"""
Transaction Pydantic schemas for validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from datetime import datetime, date as DateType
from decimal import Decimal
from enum import Enum

if TYPE_CHECKING:
    from app.schemas.account import AccountResponse
    from app.schemas.category import CategoryResponse


class TransactionType(str, Enum):
    """Transaction type enumeration."""

    INCOME = "income"
    EXPENSE = "expense"


class TransactionCreate(BaseModel):
    """
    Schema for creating a new transaction.

    Args:
        type: Transaction type (income or expense)
        amount: Transaction amount (must be positive, in the account's native
            currency — always the authoritative value for balance calculation)
        date: Transaction date
        account_id: Account ID for this transaction
        category_id: Category ID for this transaction
        title: Optional transaction title (max 100 characters)
        description: Optional description (max 500 characters)
        tags: List of tags (max 10, each max 50 characters)
        client_id: Optional client-generated UUID for offline idempotency.
            When provided, a retry of the same creation request will return
            the existing record instead of creating a duplicate.
        original_amount: Amount in the foreign currency before conversion.
            Required when original_currency is provided. Must be > 0.
        original_currency: ISO 4217 code of the foreign currency (e.g. 'USD').
            When provided, original_amount and exchange_rate are also required.
        exchange_rate: Units of account currency per 1 unit of original_currency
            at the time of the transaction. Required when original_currency is
            provided. Must be > 0.
        base_rate: Units of primaryCurrency per 1 unit of the account's native
            currency at the time of the transaction. NULL when no rate was
            available offline. Optional — the backend stores whatever the
            frontend supplies.
    """

    type: TransactionType
    amount: Decimal = Field(..., gt=0)
    date: DateType
    account_id: UUID
    category_id: UUID
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    client_id: Optional[str] = Field(None, max_length=100)
    original_amount: Optional[Decimal] = None
    original_currency: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    base_rate: Optional[Decimal] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive and round to 2 decimals."""
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return round(v, 8)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate and truncate tags."""
        if len(v) > 10:
            raise ValueError("Maximo 10 tags permitidos")
        return [tag[:50] for tag in v]

    @model_validator(mode="after")
    def validate_multi_currency_fields(self) -> "TransactionCreate":
        """
        Validate consistency of the three multi-currency fields.

        Rules:
        - If original_currency is provided, original_amount and exchange_rate
          are both required and must be > 0.
        - If original_amount or exchange_rate is provided without
          original_currency, raise ValidationError (incomplete group).
        - If none of the three are provided the transaction is treated as
          single-currency and no further validation is needed.

        Returns:
            The validated TransactionCreate instance.

        Raises:
            ValueError: If the multi-currency fields are inconsistently
                populated.
        """
        has_currency = self.original_currency is not None
        has_amount = self.original_amount is not None
        has_rate = self.exchange_rate is not None

        if has_currency:
            if not has_amount:
                raise ValueError(
                    "original_amount es requerido cuando original_currency es proporcionado"
                )
            if not has_rate:
                raise ValueError(
                    "exchange_rate es requerido cuando original_currency es proporcionado"
                )
            if self.original_amount <= 0:
                raise ValueError("original_amount debe ser mayor a 0")
            if self.exchange_rate <= 0:
                raise ValueError("exchange_rate debe ser mayor a 0")
        elif has_amount or has_rate:
            raise ValueError(
                "original_currency es requerido cuando original_amount o exchange_rate son proporcionados"
            )

        return self


class TransactionUpdate(BaseModel):
    """
    Schema for updating an existing transaction.

    All fields are optional to support partial updates.

    When any of the three multi-currency fields (original_amount,
    original_currency, exchange_rate) is present, all three must be present
    and valid.
    """

    type: Optional[TransactionType] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    date: Optional[DateType] = None
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None
    original_amount: Optional[Decimal] = None
    original_currency: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    base_rate: Optional[Decimal] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate amount is positive and round to 2 decimals if provided."""
        if v is None:
            return v
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return round(v, 8)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate and truncate tags if provided."""
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximo 10 tags permitidos")
        return [tag[:50] for tag in v]

    @model_validator(mode="after")
    def validate_multi_currency_fields(self) -> "TransactionUpdate":
        """
        Validate consistency of the three multi-currency fields when any are
        present in the update payload.

        Rules mirror TransactionCreate: if any of the three are supplied, all
        three must be supplied and original_amount / exchange_rate must be > 0.

        Returns:
            The validated TransactionUpdate instance.

        Raises:
            ValueError: If the multi-currency fields are inconsistently
                populated.
        """
        has_currency = self.original_currency is not None
        has_amount = self.original_amount is not None
        has_rate = self.exchange_rate is not None

        if has_currency or has_amount or has_rate:
            if not has_currency:
                raise ValueError(
                    "original_currency es requerido cuando original_amount o exchange_rate son proporcionados"
                )
            if not has_amount:
                raise ValueError(
                    "original_amount es requerido cuando original_currency es proporcionado"
                )
            if not has_rate:
                raise ValueError(
                    "exchange_rate es requerido cuando original_currency es proporcionado"
                )
            if self.original_amount <= 0:
                raise ValueError("original_amount debe ser mayor a 0")
            if self.exchange_rate <= 0:
                raise ValueError("exchange_rate debe ser mayor a 0")

        return self


class TransactionResponse(BaseModel):
    """
    Schema for transaction responses.

    Attributes:
        id: Transaction UUID
        type: Transaction type (income or expense)
        amount: Amount in the account's native currency (authoritative for balances)
        date: Transaction date
        account_id: Associated account UUID
        category_id: Associated category UUID
        title: Optional title
        description: Optional description
        tags: List of tags
        original_amount: Amount in the foreign currency (None for
            single-currency transactions)
        original_currency: ISO 4217 code of the foreign currency (None for
            single-currency transactions)
        exchange_rate: Rate applied at transaction time — units of account
            currency per 1 unit of original_currency (None for single-currency
            transactions)
        base_rate: Units of primaryCurrency per 1 unit of the account's native
            currency at the time of the transaction. None when unavailable offline.
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: UUID
    type: TransactionType
    amount: Decimal
    date: DateType
    account_id: UUID
    category_id: UUID
    title: Optional[str]
    description: Optional[str]
    tags: list[str]
    original_amount: Optional[Decimal] = None
    original_currency: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    base_rate: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionWithRelations(TransactionResponse):
    """
    Schema for transaction with related account and category data.

    Extends TransactionResponse with nested account and category objects.
    """

    account: "AccountResponse"
    category: "CategoryResponse"


class TransactionFilters(BaseModel):
    """
    Schema for transaction list filters.

    Args:
        account_id: Filter by account ID
        category_id: Filter by category ID
        type: Filter by transaction type
        date_from: Filter by start date (inclusive)
        date_to: Filter by end date (inclusive)
        tags: Filter by tags (any match)
        page: Page number (1-indexed)
        limit: Items per page (1-100)
    """

    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    type: Optional[TransactionType] = None
    date_from: Optional[DateType] = None
    date_to: Optional[DateType] = None
    tags: Optional[list[str]] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> "TransactionFilters":
        """Validate that date_from is before date_to."""
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from debe ser anterior a date_to")
        return self
