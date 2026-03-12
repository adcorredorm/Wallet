"""
Dashboard Pydantic schemas for consolidated views.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from typing import Optional


class AccountBalanceSummary(BaseModel):
    """Summary of account balance by currency."""

    currency: str
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
    calculation_date: date = Field(..., description="Calculation date")


class CategorySummary(BaseModel):
    """Summary of transactions by category."""

    category_id: str
    category_name: str
    total: Decimal
    transaction_count: int


class MonthlySummaryResponse(BaseModel):
    """
    Schema for monthly summary.

    Args:
        month: Month number (1-12)
        year: Year
        total_income: Total income for the month
        total_expenses: Total expenses for the month
        net: Net balance (income - expenses)
        top_expense_categories: Top expense categories
        top_income_categories: Top income categories
    """

    month: int = Field(..., ge=1, le=12)
    year: int
    total_income: Decimal
    total_expenses: Decimal
    net: Decimal
    top_expense_categories: list[CategorySummary] = Field(default_factory=list)
    top_income_categories: list[CategorySummary] = Field(default_factory=list)


class RecentActivity(BaseModel):
    """Schema for recent activity item."""

    id: str
    type: str  # 'transaction' or 'transfer'
    description: str
    amount: Decimal
    date: date


class DashboardResponse(BaseModel):
    """
    Schema for complete dashboard data.

    Returns:
        Consolidated view with net worth, monthly summary, and recent activity
    """

    net_worth: NetWorthResponse
    monthly_summary: MonthlySummaryResponse
    recent_activity: list[RecentActivity] = Field(
        default_factory=list, max_length=10
    )
