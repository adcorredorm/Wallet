"""
Dashboard service for consolidated views and reporting.
"""

from datetime import date, datetime
from decimal import Decimal
from collections import defaultdict

from sqlalchemy import func, extract

from app.extensions import db
from app.models import Account, Transaction, Transfer, TransactionType
from app.repositories import AccountRepository, TransactionRepository, TransferRepository


class DashboardService:
    """Service for dashboard and reporting logic."""

    def __init__(self):
        """Initialize dashboard service with repositories."""
        self.account_repository = AccountRepository()
        self.transaction_repository = TransactionRepository()
        self.transfer_repository = TransferRepository()

    def get_net_worth(self) -> dict[str, list[dict]]:
        """
        Calculate net worth grouped by currency.

        Returns:
            Dictionary with balances by currency and calculation date
        """
        active_accounts = self.account_repository.get_all_active()

        # Group accounts by currency and calculate total balance
        balances_by_currency = defaultdict(Decimal)

        for account in active_accounts:
            balance = self.account_repository.calculate_balance(account.id)
            balances_by_currency[account.currency] += balance

        # Format response
        balances = [
            {"currency": currency, "total": float(total)}
            for currency, total in balances_by_currency.items()
        ]

        return {
            "balances": balances,
            "calculation_date": date.today(),
        }

    def get_monthly_summary(self, month: int, year: int) -> dict:
        """
        Get summary of income and expenses for a specific month.

        Args:
            month: Month number (1-12)
            year: Year

        Returns:
            Dictionary with monthly summary data
        """
        # Get total income for the month
        total_income = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.type == TransactionType.INCOME,
                extract("month", Transaction.date) == month,
                extract("year", Transaction.date) == year,
            )
            .scalar()
        ) or Decimal("0")

        # Get total expenses for the month
        total_expenses = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.type == TransactionType.EXPENSE,
                extract("month", Transaction.date) == month,
                extract("year", Transaction.date) == year,
            )
            .scalar()
        ) or Decimal("0")

        # Calculate net balance
        net = Decimal(str(total_income)) - Decimal(str(total_expenses))

        # Get top expense categories
        from app.models import Category

        top_expenses = (
            db.session.query(
                Category.id,
                Category.name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .join(Transaction)
            .filter(
                Transaction.type == TransactionType.EXPENSE,
                extract("month", Transaction.date) == month,
                extract("year", Transaction.date) == year,
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(5)
            .all()
        )

        # Get top income categories
        top_income = (
            db.session.query(
                Category.id,
                Category.name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .join(Transaction)
            .filter(
                Transaction.type == TransactionType.INCOME,
                extract("month", Transaction.date) == month,
                extract("year", Transaction.date) == year,
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(5)
            .all()
        )

        return {
            "month": month,
            "year": year,
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net": float(net),
            "top_expense_categories": [
                {
                    "category_id": str(cat.id),
                    "category_name": cat.name,
                    "total": float(cat.total),
                    "transaction_count": cat.count,
                }
                for cat in top_expenses
            ],
            "top_income_categories": [
                {
                    "category_id": str(cat.id),
                    "category_name": cat.name,
                    "total": float(cat.total),
                    "transaction_count": cat.count,
                }
                for cat in top_income
            ],
        }

    def get_recent_activity(self, limit: int = 10) -> list[dict]:
        """
        Get recent transactions and transfers combined.

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of recent activities sorted by date
        """
        # Get recent transactions
        recent_transactions = self.transaction_repository.get_recent(limit=limit)

        # Get recent transfers
        recent_transfers = self.transfer_repository.get_recent(limit=limit)

        # Combine and format
        activities = []

        for trans in recent_transactions:
            activities.append(
                {
                    "id": str(trans.id),
                    "type": "transaction",
                    "subtype": trans.type.value,
                    "description": trans.title or f"{trans.type.value.title()} - {trans.category.name}",
                    "amount": float(trans.amount),
                    "date": trans.date,
                    "account": trans.account.name,
                }
            )

        for transfer in recent_transfers:
            activities.append(
                {
                    "id": str(transfer.id),
                    "type": "transfer",
                    "description": transfer.description
                    or f"Transferencia: {transfer.source_account.name} → {transfer.destination_account.name}",
                    "amount": float(transfer.amount),
                    "date": transfer.date,
                    "source_account": transfer.source_account.name,
                    "destination_account": transfer.destination_account.name,
                }
            )

        # Sort by date (most recent first)
        activities.sort(key=lambda x: x["date"], reverse=True)

        return activities[:limit]

    def get_dashboard_data(self, month: int | None = None, year: int | None = None) -> dict:
        """
        Get complete dashboard data.

        Args:
            month: Month for summary (defaults to current month)
            year: Year for summary (defaults to current year)

        Returns:
            Complete dashboard data with net worth, monthly summary, and recent activity
        """
        today = date.today()
        month = month or today.month
        year = year or today.year

        return {
            "net_worth": self.get_net_worth(),
            "monthly_summary": self.get_monthly_summary(month, year),
            "recent_activity": self.get_recent_activity(limit=10),
        }
