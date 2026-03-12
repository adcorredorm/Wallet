"""
Transfer Pydantic schemas for validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal

if TYPE_CHECKING:
    from app.schemas.account import AccountResponse


class TransferCreate(BaseModel):
    """
    Schema for creating a new transfer.

    Args:
        source_account_id: Source account ID
        destination_account_id: Destination account ID
        amount: Transfer amount (must be positive, 2 decimal places)
        date: Transfer date
        description: Optional description (max 500 characters)
        tags: List of tags (max 10, each max 50 characters)
        client_id: Optional client-generated UUID for offline idempotency.
            When provided, a retry of the same creation request will return
            the existing record instead of creating a duplicate.

    Raises:
        ValueError: If source and destination accounts are the same
    """

    source_account_id: UUID
    destination_account_id: UUID
    amount: Decimal = Field(..., gt=0)
    date: date
    description: Optional[str] = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    client_id: Optional[str] = Field(None, max_length=100)

    @model_validator(mode="after")
    def validate_different_accounts(self) -> "TransferCreate":
        """Validate that source and destination accounts are different."""
        if self.source_account_id == self.destination_account_id:
            raise ValueError("No se puede transferir a la misma cuenta")
        return self

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive and round to 2 decimals."""
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return round(v, 2)

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
    Note: Cannot change source or destination accounts.
    """

    amount: Optional[Decimal] = Field(None, gt=0)
    date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate amount is positive and round to 2 decimals if provided."""
        if v is None:
            return v
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return round(v, 2)

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

    Returns:
        Complete transfer information including metadata
    """

    id: UUID
    source_account_id: UUID
    destination_account_id: UUID
    amount: Decimal
    date: date
    description: Optional[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime

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
        limit: Items per page (1-100)
    """

    account_id: Optional[UUID] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    tags: Optional[list[str]] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> "TransferFilters":
        """Validate that date_from is before date_to."""
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from debe ser anterior a date_to")
        return self
