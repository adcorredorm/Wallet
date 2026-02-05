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

    INGRESO = "ingreso"
    GASTO = "gasto"


class TransactionCreate(BaseModel):
    """
    Schema for creating a new transaction.

    Args:
        tipo: Transaction type (income or expense)
        monto: Transaction amount (must be positive, 2 decimal places)
        fecha: Transaction date
        cuenta_id: Account ID for this transaction
        categoria_id: Category ID for this transaction
        titulo: Optional transaction title (max 100 characters)
        descripcion: Optional description (max 500 characters)
        tags: List of tags (max 10, each max 50 characters)
    """

    tipo: TransactionType
    monto: Decimal = Field(..., gt=0)
    fecha: date
    cuenta_id: UUID
    categoria_id: UUID
    titulo: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)

    @field_validator("monto")
    @classmethod
    def validate_monto(cls, v: Decimal) -> Decimal:
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

    tipo: Optional[TransactionType] = None
    monto: Optional[Decimal] = Field(None, gt=0)
    fecha: Optional[date] = None
    cuenta_id: Optional[UUID] = None
    categoria_id: Optional[UUID] = None
    titulo: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None

    @field_validator("monto")
    @classmethod
    def validate_monto(cls, v: Optional[Decimal]) -> Optional[Decimal]:
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
    tipo: TransactionType
    monto: Decimal
    fecha: date
    cuenta_id: UUID
    categoria_id: UUID
    titulo: Optional[str]
    descripcion: Optional[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionWithRelations(TransactionResponse):
    """
    Schema for transaction with related account and category data.

    Extends TransactionResponse with nested account and category objects.
    """

    cuenta: "AccountResponse"
    categoria: "CategoryResponse"


class TransactionFilters(BaseModel):
    """
    Schema for transaction list filters.

    Args:
        cuenta_id: Filter by account ID
        categoria_id: Filter by category ID
        tipo: Filter by transaction type
        fecha_desde: Filter by start date (inclusive)
        fecha_hasta: Filter by end date (inclusive)
        tags: Filter by tags (any match)
        page: Page number (1-indexed)
        limit: Items per page (1-100)
    """

    cuenta_id: Optional[UUID] = None
    categoria_id: Optional[UUID] = None
    tipo: Optional[TransactionType] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    tags: Optional[list[str]] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> "TransactionFilters":
        """Validate that fecha_desde is before fecha_hasta."""
        if self.fecha_desde and self.fecha_hasta:
            if self.fecha_desde > self.fecha_hasta:
                raise ValueError("fecha_desde debe ser anterior a fecha_hasta")
        return self
