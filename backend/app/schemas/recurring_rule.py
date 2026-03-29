"""
Pydantic schemas for RecurringRule validation and serialization.
"""

from datetime import date as DateType, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RecurringFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurringRuleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class RecurringRuleCreate(BaseModel):
    """Schema for creating a new recurring rule."""

    offline_id: str = Field(..., max_length=100)
    title: str = Field(..., max_length=100)
    type: TransactionType
    amount: Decimal = Field(..., gt=0)
    account_id: UUID
    category_id: UUID
    description: Optional[str] = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    frequency: RecurringFrequency
    interval: int = Field(default=1, ge=1)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    start_date: DateType
    end_date: Optional[DateType] = None
    max_occurrences: Optional[int] = Field(None, ge=1)
    next_occurrence_date: DateType
    status: RecurringRuleStatus = RecurringRuleStatus.ACTIVE

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return round(v, 8)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        if len(v) > 10:
            raise ValueError("Maximo 10 tags permitidos")
        return [tag[:50] for tag in v]


class RecurringRuleUpdate(BaseModel):
    """Schema for updating an existing recurring rule. All fields optional."""

    title: Optional[str] = Field(None, max_length=100)
    amount: Optional[Decimal] = Field(None, gt=0)
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None
    requires_confirmation: Optional[bool] = None
    frequency: Optional[RecurringFrequency] = None
    interval: Optional[int] = Field(None, ge=1)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    end_date: Optional[DateType] = None
    max_occurrences: Optional[int] = Field(None, ge=1)
    next_occurrence_date: Optional[DateType] = None
    occurrences_created: Optional[int] = Field(None, ge=0)
    status: Optional[RecurringRuleStatus] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return round(v, 8)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximo 10 tags permitidos")
        return [tag[:50] for tag in v]


class RecurringRuleResponse(BaseModel):
    """Schema for recurring rule API responses."""

    id: UUID
    offline_id: Optional[str]
    user_id: Optional[UUID]
    title: str
    type: TransactionType
    amount: Decimal
    account_id: UUID
    category_id: UUID
    description: Optional[str]
    tags: list[str]
    requires_confirmation: bool
    frequency: RecurringFrequency
    interval: int
    day_of_month: Optional[int]
    start_date: DateType
    end_date: Optional[DateType]
    max_occurrences: Optional[int]
    occurrences_created: int
    next_occurrence_date: DateType
    status: RecurringRuleStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecurringRuleFilters(BaseModel):
    """Schema for list/filter query parameters."""

    status: Optional[RecurringRuleStatus] = None
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=10000)
