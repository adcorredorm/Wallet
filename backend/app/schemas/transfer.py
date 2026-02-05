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
        cuenta_origen_id: Source account ID
        cuenta_destino_id: Destination account ID
        monto: Transfer amount (must be positive, 2 decimal places)
        fecha: Transfer date
        descripcion: Optional description (max 500 characters)
        tags: List of tags (max 10, each max 50 characters)

    Raises:
        ValueError: If source and destination accounts are the same
    """

    cuenta_origen_id: UUID
    cuenta_destino_id: UUID
    monto: Decimal = Field(..., gt=0)
    fecha: date
    descripcion: Optional[str] = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_different_accounts(self) -> "TransferCreate":
        """Validate that source and destination accounts are different."""
        if self.cuenta_origen_id == self.cuenta_destino_id:
            raise ValueError("No se puede transferir a la misma cuenta")
        return self

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


class TransferUpdate(BaseModel):
    """
    Schema for updating an existing transfer.

    All fields are optional to support partial updates.
    Note: Cannot change source or destination accounts.
    """

    monto: Optional[Decimal] = Field(None, gt=0)
    fecha: Optional[date] = None
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


class TransferResponse(BaseModel):
    """
    Schema for transfer responses.

    Returns:
        Complete transfer information including metadata
    """

    id: UUID
    cuenta_origen_id: UUID
    cuenta_destino_id: UUID
    monto: Decimal
    fecha: date
    descripcion: Optional[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransferWithRelations(TransferResponse):
    """
    Schema for transfer with related account data.

    Extends TransferResponse with nested account objects.
    """

    cuenta_origen: "AccountResponse"
    cuenta_destino: "AccountResponse"


class TransferFilters(BaseModel):
    """
    Schema for transfer list filters.

    Args:
        cuenta_id: Filter by either source or destination account
        fecha_desde: Filter by start date (inclusive)
        fecha_hasta: Filter by end date (inclusive)
        tags: Filter by tags (any match)
        page: Page number (1-indexed)
        limit: Items per page (1-100)
    """

    cuenta_id: Optional[UUID] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    tags: Optional[list[str]] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> "TransferFilters":
        """Validate that fecha_desde is before fecha_hasta."""
        if self.fecha_desde and self.fecha_hasta:
            if self.fecha_desde > self.fecha_hasta:
                raise ValueError("fecha_desde debe ser anterior a fecha_hasta")
        return self
