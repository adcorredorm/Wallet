"""
Dashboard Pydantic schemas for consolidated views.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from typing import Optional


class AccountBalanceSummary(BaseModel):
    """Summary of account balance by currency."""

    divisa: str
    total: Decimal


class NetWorthResponse(BaseModel):
    """
    Schema for net worth calculation.

    Returns:
        List of total balances grouped by currency
    """

    balances: list[AccountBalanceSummary] = Field(
        ..., description="Total balances by currency"
    )
    fecha_calculo: date = Field(..., description="Calculation date")


class CategorySummary(BaseModel):
    """Summary of transactions by category."""

    categoria_id: str
    categoria_nombre: str
    total: Decimal
    cantidad_transacciones: int


class MonthlySummaryResponse(BaseModel):
    """
    Schema for monthly summary.

    Args:
        mes: Month number (1-12)
        anio: Year
        total_ingresos: Total income for the month
        total_gastos: Total expenses for the month
        neto: Net balance (income - expenses)
        top_categorias_gasto: Top expense categories
        top_categorias_ingreso: Top income categories
    """

    mes: int = Field(..., ge=1, le=12)
    anio: int
    total_ingresos: Decimal
    total_gastos: Decimal
    neto: Decimal
    top_categorias_gasto: list[CategorySummary] = Field(default_factory=list)
    top_categorias_ingreso: list[CategorySummary] = Field(default_factory=list)


class RecentActivity(BaseModel):
    """Schema for recent activity item."""

    id: str
    tipo: str  # 'transaccion' or 'transferencia'
    descripcion: str
    monto: Decimal
    fecha: date


class DashboardResponse(BaseModel):
    """
    Schema for complete dashboard data.

    Returns:
        Consolidated view with net worth, monthly summary, and recent activity
    """

    patrimonio_neto: NetWorthResponse
    resumen_mensual: MonthlySummaryResponse
    actividad_reciente: list[RecentActivity] = Field(
        default_factory=list, max_length=10
    )
