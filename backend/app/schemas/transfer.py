"""
Transfer Pydantic schemas for validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from datetime import datetime, date as DateType
from decimal import Decimal

if TYPE_CHECKING:
    from app.schemas.account import AccountResponse


class TransferCreate(BaseModel):
    """
    Schema for creating a new transfer.

    Args:
        source_account_id: Source account ID
        destination_account_id: Destination account ID
        amount: Transfer amount in source currency (must be positive)
        date: Transfer date
        description: Optional description (max 500 characters)
        tags: List of tags (max 10, each max 50 characters)
        offline_id: Optional client-generated UUID for offline idempotency.
            When provided, a retry of the same creation request will return
            the existing record instead of creating a duplicate.
        destination_amount: Amount credited to the destination account in its
            currency. Required when transferring between accounts with different
            currencies. Must be positive when provided.
        exchange_rate: Exchange rate applied at transfer time (source / destination
            currency ratio). Required when transferring between accounts with
            different currencies. Must be positive when provided.
        destination_currency: ISO 4217 currency code of the destination account.
            Auto-derived from the destination account in the service layer;
            clients do not need to supply this field.
        base_rate: Units of primaryCurrency per 1 unit of the source account's
            native currency at the time of the transfer. Optional, nullable.

    Raises:
        ValueError: If source and destination accounts are the same, or if
            destination_amount / exchange_rate are provided but not positive.
    """

    model_config = {"extra": "ignore"}

    source_account_id: UUID
    destination_account_id: UUID
    amount: Decimal = Field(..., gt=0)
    date: DateType
    description: Optional[str] = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    title: Optional[str] = Field(None, max_length=100)
    offline_id: Optional[str] = Field(None, max_length=100)
    destination_amount: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    destination_currency: Optional[str] = Field(None, max_length=10)
    base_rate: Optional[Decimal] = None

    @model_validator(mode="after")
    def validate_transfer(self) -> "TransferCreate":
        """
        Validate transfer-level constraints.

        Checks:
        - Source and destination accounts must differ.
        - destination_amount, when provided, must be > 0.
        - exchange_rate, when provided, must be > 0.
        Cross-currency requirement (comparing account currencies) is enforced
        in the service layer where account records are available.

        Returns:
            The validated TransferCreate instance.

        Raises:
            ValueError: If any constraint is violated.
        """
        if self.source_account_id == self.destination_account_id:
            raise ValueError("No se puede transferir a la misma cuenta")
        if self.destination_amount is not None and self.destination_amount <= 0:
            raise ValueError("destination_amount debe ser mayor a 0")
        if self.exchange_rate is not None and self.exchange_rate <= 0:
            raise ValueError("exchange_rate debe ser mayor a 0")
        return self

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


class TransferUpdate(BaseModel):
    """
    Schema for updating an existing transfer.

    All fields are optional to support partial updates.
    Note: Cannot change source or destination accounts, and therefore cannot
    change the same-currency vs. cross-currency nature of the transfer.

    Args:
        amount: New transfer amount in source currency. Must be positive.
        date: New transfer date.
        description: New description (max 500 characters).
        tags: New list of tags (max 10, each max 50 characters).
        destination_amount: New destination amount. Must be positive when
            provided. Only meaningful on cross-currency transfers.
        exchange_rate: New exchange rate. Must be positive when provided.
            Only meaningful on cross-currency transfers.
        base_rate: Units of primaryCurrency per 1 unit of the source account's
            native currency at the time of the transfer. Optional, nullable.
    """

    model_config = {"extra": "ignore"}

    amount: Optional[Decimal] = Field(None, gt=0)
    date: Optional[DateType] = None
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None
    destination_amount: Optional[Decimal] = None
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


class TransferResponse(BaseModel):
    """
    Schema for transfer responses.

    Attributes:
        id: Transfer UUID
        source_account_id: Source account UUID
        destination_account_id: Destination account UUID
        amount: Transfer amount in source currency
        date: Transfer date
        description: Optional description
        tags: List of tags
        created_at: Creation timestamp
        updated_at: Last update timestamp
        destination_amount: Amount credited to destination account in its
            currency. None for same-currency transfers.
        exchange_rate: Exchange rate applied at transfer time. None for
            same-currency transfers.
        destination_currency: ISO 4217 currency code of the destination
            account. None for same-currency transfers.
        base_rate: Units of primaryCurrency per 1 unit of the source account's
            native currency at the time of the transfer. None when unavailable
            offline.
    """

    id: UUID
    source_account_id: UUID
    destination_account_id: UUID
    amount: Decimal
    date: DateType
    title: Optional[str] = None
    description: Optional[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    destination_amount: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    destination_currency: Optional[str] = None
    base_rate: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class TransferWithRelations(TransferResponse):
    """
    Schema for transfer with related account data.

    Extends TransferResponse with nested account objects.
    """

    source_account: "AccountResponse"
    destination_account: "AccountResponse"


class TransferFilters(BaseModel):
    """
    Schema for transfer list filters.

    Args:
        account_id: Filter by either source or destination account
        date_from: Filter by start date (inclusive)
        date_to: Filter by end date (inclusive)
        tags: Filter by tags (any match)
        page: Page number (1-indexed)
        limit: Items per page (1-10000)
    """

    account_id: Optional[UUID] = None
    date_from: Optional[DateType] = None
    date_to: Optional[DateType] = None
    tags: Optional[list[str]] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=10000)

    @model_validator(mode="after")
    def validate_date_range(self) -> "TransferFilters":
        """Validate that date_from is before date_to."""
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from debe ser anterior a date_to")
        return self
