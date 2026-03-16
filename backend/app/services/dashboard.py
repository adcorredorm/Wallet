"""
Dashboard service for consolidated views and reporting.

Every public method accepts a user_id parameter and passes it to the
repository so queries are always scoped to a single user.
"""

from datetime import date, datetime
from decimal import Decimal
from collections import defaultdict
from uuid import UUID

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

    def get_net_worth(self, user_id: UUID) -> dict[str, list[dict]]:
        """
        Calculate net worth grouped by currency for a user.

        Args:
            user_id: Owner's UUID.

        Returns:
            Dictionary with balances by currency and calculation date.
        """
        active_accounts = self.account_repository.get_all_active(user_id=user_id)

        balances_by_currency: dict[str, Decimal] = defaultdict(Decimal)

        for account in active_accounts:
            balance = self.account_repository.calculate_balance(account.id, user_id)
            balances_by_currency[account.currency] += balance

        balances = [
            {"currency": currency, "total": float(total)}
            for currency, total in balances_by_currency.items()
        ]

        return {
            "balances": balances,
            "calculation_date": date.today(),
        }

    def get_monthly_summary(self, user_id: UUID, month: int, year: int) -> dict:
        """
        Get summary of income and expenses for a specific month for a user.

        Args:
            user_id: Owner's UUID.
            month: Month number (1-12).
            year: Year.

        Returns:
            Dictionary with monthly summary data.
        """
        total_income = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.INCOME,
                extract("month", Transaction.date) == month,
                extract("year", Transaction.date) == year,
            )
            .scalar()
        ) or Decimal("0")

        total_expenses = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                extract("month", Transaction.date) == month,
                extract("year", Transaction.date) == year,
            )
            .scalar()
        ) or Decimal("0")

        net = Decimal(str(total_income)) - Decimal(str(total_expenses))

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
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                extract("month", Transaction.date) == month,
                extract("year", Transaction.date) == year,
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(5)
            .all()
        )

        top_income = (
            db.session.query(
                Category.id,
                Category.name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .join(Transaction)
            .filter(
                Transaction.user_id == user_id,
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

    def get_recent_activity(self, user_id: UUID, limit: int = 10) -> list[dict]:
        """
        Get recent transactions and transfers combined for a user.

        Args:
            user_id: Owner's UUID.
            limit: Maximum number of activities to return.

        Returns:
            List of recent activities sorted by date.
        """
        recent_transactions = self.transaction_repository.get_recent(
            user_id=user_id, limit=limit
        )
        recent_transfers = self.transfer_repository.get_recent(
            user_id=user_id, limit=limit
        )

        activities = []

        for trans in recent_transactions:
            activities.append(
                {
                    "id": str(trans.id),
                    "type": "transaction",
                    "subtype": trans.type.value,
                    "description": trans.title
                    or f"{trans.type.value.title()} - {trans.category.name}",
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
                    or (
                        f"Transferencia: {transfer.source_account.name} "
                        f"→ {transfer.destination_account.name}"
                    ),
                    "amount": float(transfer.amount),
                    "date": transfer.date,
                    "source_account": transfer.source_account.name,
                    "destination_account": transfer.destination_account.name,
                }
            )

        activities.sort(key=lambda x: x["date"], reverse=True)

        return activities[:limit]

    def get_dashboard_data(
        self, user_id: UUID, month: int | None = None, year: int | None = None
    ) -> dict:
        """
        Get complete dashboard data for a user.

        Args:
            user_id: Owner's UUID.
            month: Month for summary (defaults to current month).
            year: Year for summary (defaults to current year).

        Returns:
            Complete dashboard data with net worth, monthly summary, and recent
            activity.
        """
        today = date.today()
        month = month or today.month
        year = year or today.year

        return {
            "net_worth": self.get_net_worth(user_id=user_id),
            "monthly_summary": self.get_monthly_summary(
                user_id=user_id, month=month, year=year
            ),
            "recent_activity": self.get_recent_activity(user_id=user_id, limit=10),
        }
