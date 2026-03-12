"""
Transaction Pydantic schemas for validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from datetime import datetime, date
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
        amount: Transaction amount (must be positive, 2 decimal places)
        date: Transaction date
        account_id: Account ID for this transaction
        category_id: Category ID for this transaction
        title: Optional transaction title (max 100 characters)
        description: Optional description (max 500 characters)
        tags: List of tags (max 10, each max 50 characters)
        client_id: Optional client-generated UUID for offline idempotency.
            When provided, a retry of the same creation request will return
            the existing record instead of creating a duplicate.
    """

    type: TransactionType
    amount: Decimal = Field(..., gt=0)
    date: date
    account_id: UUID
    category_id: UUID
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    client_id: Optional[str] = Field(None, max_length=100)

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


class TransactionUpdate(BaseModel):
    """
    Schema for updating an existing transaction.

    All fields are optional to support partial updates.
    """

    type: Optional[TransactionType] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    date: Optional[date] = None
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    title: Optional[str] = Field(None, max_length=100)
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


class TransactionResponse(BaseModel):
    """
    Schema for transaction responses.

    Returns:
        Complete transaction information including metadata
    """

    id: UUID
    type: TransactionType
    amount: Decimal
    date: date
    account_id: UUID
    category_id: UUID
    title: Optional[str]
    description: Optional[str]
    tags: list[str]
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
    date_from: Optional[date] = None
    date_to: Optional[date] = None
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
