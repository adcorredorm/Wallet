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
            balances_by_currency[account.divisa] += balance

        # Format response
        balances = [
            {"divisa": divisa, "total": float(total)}
            for divisa, total in balances_by_currency.items()
        ]

        return {
            "balances": balances,
            "fecha_calculo": date.today(),
        }

    def get_monthly_summary(self, mes: int, anio: int) -> dict:
        """
        Get summary of income and expenses for a specific month.

        Args:
            mes: Month number (1-12)
            anio: Year

        Returns:
            Dictionary with monthly summary data
        """
        # Get total income for the month
        total_ingresos = (
            db.session.query(func.coalesce(func.sum(Transaction.monto), 0))
            .filter(
                Transaction.tipo == TransactionType.INGRESO,
                extract("month", Transaction.fecha) == mes,
                extract("year", Transaction.fecha) == anio,
            )
            .scalar()
        ) or Decimal("0")

        # Get total expenses for the month
        total_gastos = (
            db.session.query(func.coalesce(func.sum(Transaction.monto), 0))
            .filter(
                Transaction.tipo == TransactionType.GASTO,
                extract("month", Transaction.fecha) == mes,
                extract("year", Transaction.fecha) == anio,
            )
            .scalar()
        ) or Decimal("0")

        # Calculate net balance
        neto = Decimal(str(total_ingresos)) - Decimal(str(total_gastos))

        # Get top expense categories
        from app.models import Category

        top_gastos = (
            db.session.query(
                Category.id,
                Category.nombre,
                func.sum(Transaction.monto).label("total"),
                func.count(Transaction.id).label("cantidad"),
            )
            .join(Transaction)
            .filter(
                Transaction.tipo == TransactionType.GASTO,
                extract("month", Transaction.fecha) == mes,
                extract("year", Transaction.fecha) == anio,
            )
            .group_by(Category.id, Category.nombre)
            .order_by(func.sum(Transaction.monto).desc())
            .limit(5)
            .all()
        )

        # Get top income categories
        top_ingresos = (
            db.session.query(
                Category.id,
                Category.nombre,
                func.sum(Transaction.monto).label("total"),
                func.count(Transaction.id).label("cantidad"),
            )
            .join(Transaction)
            .filter(
                Transaction.tipo == TransactionType.INGRESO,
                extract("month", Transaction.fecha) == mes,
                extract("year", Transaction.fecha) == anio,
            )
            .group_by(Category.id, Category.nombre)
            .order_by(func.sum(Transaction.monto).desc())
            .limit(5)
            .all()
        )

        return {
            "mes": mes,
            "anio": anio,
            "total_ingresos": float(total_ingresos),
            "total_gastos": float(total_gastos),
            "neto": float(neto),
            "top_categorias_gasto": [
                {
                    "categoria_id": str(cat.id),
                    "categoria_nombre": cat.nombre,
                    "total": float(cat.total),
                    "cantidad_transacciones": cat.cantidad,
                }
                for cat in top_gastos
            ],
            "top_categorias_ingreso": [
                {
                    "categoria_id": str(cat.id),
                    "categoria_nombre": cat.nombre,
                    "total": float(cat.total),
                    "cantidad_transacciones": cat.cantidad,
                }
                for cat in top_ingresos
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
                    "tipo": "transaccion",
                    "subtipo": trans.tipo.value,
                    "descripcion": trans.titulo or f"{trans.tipo.value.title()} - {trans.categoria.nombre}",
                    "monto": float(trans.monto),
                    "fecha": trans.fecha,
                    "cuenta": trans.cuenta.nombre,
                }
            )

        for transfer in recent_transfers:
            activities.append(
                {
                    "id": str(transfer.id),
                    "tipo": "transferencia",
                    "descripcion": transfer.descripcion
                    or f"Transferencia: {transfer.cuenta_origen.nombre} → {transfer.cuenta_destino.nombre}",
                    "monto": float(transfer.monto),
                    "fecha": transfer.fecha,
                    "cuenta_origen": transfer.cuenta_origen.nombre,
                    "cuenta_destino": transfer.cuenta_destino.nombre,
                }
            )

        # Sort by date (most recent first)
        activities.sort(key=lambda x: x["fecha"], reverse=True)

        return activities[:limit]

    def get_dashboard_data(self, mes: int | None = None, anio: int | None = None) -> dict:
        """
        Get complete dashboard data.

        Args:
            mes: Month for summary (defaults to current month)
            anio: Year for summary (defaults to current year)

        Returns:
            Complete dashboard data with net worth, monthly summary, and recent activity
        """
        today = date.today()
        mes = mes or today.month
        anio = anio or today.year

        return {
            "patrimonio_neto": self.get_net_worth(),
            "resumen_mensual": self.get_monthly_summary(mes, anio),
            "actividad_reciente": self.get_recent_activity(limit=10),
        }
