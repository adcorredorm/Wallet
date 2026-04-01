# backend/app/schemas/budget.py
from datetime import date as DateType, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class BudgetType(str, Enum):
    RECURRING = "recurring"
    ONE_TIME = "one_time"


class BudgetStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class BudgetFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class BudgetCreate(BaseModel):
    offline_id: str = Field(..., max_length=100)
    name: str = Field(..., max_length=100)
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    amount_limit: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    budget_type: BudgetType
    frequency: Optional[BudgetFrequency] = None
    interval: int = Field(default=1, ge=1)
    reference_date: Optional[DateType] = None
    start_date: Optional[DateType] = None
    end_date: Optional[DateType] = None
    status: BudgetStatus = BudgetStatus.ACTIVE
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=7)

    @model_validator(mode="after")
    def validate_scope_and_type(self) -> "BudgetCreate":
        has_account = self.account_id is not None
        has_category = self.category_id is not None
        if has_account == has_category:
            raise ValueError(
                "Exactamente uno de account_id o category_id debe estar presente"
            )
        if self.budget_type == BudgetType.RECURRING:
            if self.frequency is None:
                raise ValueError("frequency es requerido para presupuestos recurrentes")
        elif self.budget_type == BudgetType.ONE_TIME:
            if self.start_date is None or self.end_date is None:
                raise ValueError(
                    "start_date y end_date son requeridos para presupuestos puntuales"
                )
            if self.end_date <= self.start_date:
                raise ValueError("end_date debe ser posterior a start_date")
        return self


class BudgetUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    amount_limit: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    frequency: Optional[BudgetFrequency] = None
    interval: Optional[int] = Field(None, ge=1)
    reference_date: Optional[DateType] = None
    start_date: Optional[DateType] = None
    end_date: Optional[DateType] = None
    status: Optional[BudgetStatus] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=7)


class BudgetResponse(BaseModel):
    id: UUID
    offline_id: Optional[str]
    user_id: Optional[UUID]
    name: str
    account_id: Optional[UUID]
    category_id: Optional[UUID]
    amount_limit: Decimal
    currency: str
    budget_type: BudgetType
    frequency: Optional[BudgetFrequency]
    interval: Optional[int]
    reference_date: Optional[DateType]
    start_date: Optional[DateType]
    end_date: Optional[DateType]
    status: BudgetStatus
    icon: Optional[str]
    color: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
