"""
Unit tests for DashboardService.

These tests focus on business logic validation using mocked repositories
and a patched db.session for methods that bypass the repository layer and
query SQLAlchemy directly.

No real database, no Flask app context — pure unit tests.
"""

import pytest
from decimal import Decimal
from datetime import date
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch

from app.services.dashboard import DashboardService
from app.models.account import Account
from app.models.transaction import Transaction, TransactionType
from app.models.transfer import Transfer


# ============================================================================
# LOCAL FIXTURES
# ============================================================================

@pytest.fixture
def mock_account_repo():
    """Create a mocked AccountRepository patched at the service module level."""
    with patch('app.services.dashboard.AccountRepository') as mock:
        yield mock.return_value


@pytest.fixture
def mock_transaction_repo():
    """Create a mocked TransactionRepository patched at the service module level."""
    with patch('app.services.dashboard.TransactionRepository') as mock:
        yield mock.return_value


@pytest.fixture
def mock_transfer_repo():
    """Create a mocked TransferRepository patched at the service module level."""
    with patch('app.services.dashboard.TransferRepository') as mock:
        yield mock.return_value


@pytest.fixture
def mock_db():
    """
    Patch db at the service module level.

    The mock_query object collapses every SQLAlchemy builder method
    (.filter, .join, .group_by, .order_by, .limit) back onto itself so that
    any arbitrary chain resolves without error.  .scalar() returns Decimal("0")
    and .all() returns [] by default.
    """
    with patch('app.services.dashboard.db') as mock:
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.scalar.return_value = Decimal("0")
        mock_query.all.return_value = []
        mock.session.query.return_value = mock_query
        yield mock


@pytest.fixture
def dashboard_service(
    mock_account_repo, mock_transaction_repo, mock_transfer_repo, mock_db
):
    """
    Create a DashboardService instance with all dependencies mocked.

    All four patch fixtures must be active before DashboardService() is called.
    Repository attributes are then overwritten for deterministic access.
    """
    service = DashboardService()
    service.account_repository = mock_account_repo
    service.transaction_repository = mock_transaction_repo
    service.transfer_repository = mock_transfer_repo
    return service


# ============================================================================
# HELPERS
# ============================================================================

def _make_mock_transaction(tipo: TransactionType = TransactionType.GASTO) -> Mock:
    """
    Build a Transaction mock suitable for get_recent_activity.

    The service accesses trans.categoria.nombre and trans.cuenta.nombre when
    formatting recent activity, so those nested attributes must exist.
    """
    trans = MagicMock()
    trans.id = uuid4()
    trans.tipo = tipo
    trans.monto = Decimal("100.00")
    trans.fecha = date(2026, 3, 1)
    trans.titulo = None  # triggers the fallback description path

    categoria = Mock()
    categoria.nombre = "Categoría test"
    trans.categoria = categoria

    cuenta = Mock()
    cuenta.nombre = "Cuenta test"
    trans.cuenta = cuenta

    return trans


def _make_mock_transfer() -> Mock:
    """
    Build a Transfer mock suitable for get_recent_activity.

    The service accesses transfer.cuenta_origen.nombre and
    transfer.cuenta_destino.nombre when formatting recent activity.
    """
    transfer = MagicMock()
    transfer.id = uuid4()
    transfer.monto = Decimal("200.00")
    transfer.fecha = date(2026, 3, 1)
    transfer.descripcion = None  # triggers the fallback description path

    cuenta_origen = Mock()
    cuenta_origen.nombre = "Origen test"
    transfer.cuenta_origen = cuenta_origen

    cuenta_destino = Mock()
    cuenta_destino.nombre = "Destino test"
    transfer.cuenta_destino = cuenta_destino

    return transfer


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestGetNetWorth:
    """Tests for DashboardService.get_net_worth."""

    def test_get_net_worth_groups_by_currency(
        self, dashboard_service, mock_account_repo
    ):
        """Should group account balances by currency and sum them correctly."""
        account_mxn_1 = MagicMock()
        account_mxn_1.id = uuid4()
        account_mxn_1.divisa = "MXN"

        account_mxn_2 = MagicMock()
        account_mxn_2.id = uuid4()
        account_mxn_2.divisa = "MXN"

        account_usd = MagicMock()
        account_usd.id = uuid4()
        account_usd.divisa = "USD"

        mock_account_repo.get_all_active.return_value = [
            account_mxn_1, account_mxn_2, account_usd
        ]
        mock_account_repo.calculate_balance.side_effect = [
            Decimal("1000.00"),
            Decimal("500.00"),
            Decimal("200.00"),
        ]

        result = dashboard_service.get_net_worth()

        balances = {b["divisa"]: b["total"] for b in result["balances"]}
        assert balances["MXN"] == 1500.0  # 1000 + 500
        assert balances["USD"] == 200.0
        assert "fecha_calculo" in result

    def test_get_net_worth_empty_accounts_returns_empty_balances(
        self, dashboard_service, mock_account_repo
    ):
        """Should return an empty balances list when no active accounts exist."""
        mock_account_repo.get_all_active.return_value = []

        result = dashboard_service.get_net_worth()

        assert result["balances"] == []
        assert "fecha_calculo" in result

    def test_get_net_worth_calls_calculate_balance_for_each_account(
        self, dashboard_service, mock_account_repo
    ):
        """Should call calculate_balance once per active account."""
        accounts = [Mock(spec=Account, id=uuid4(), divisa="MXN") for _ in range(3)]
        mock_account_repo.get_all_active.return_value = accounts
        mock_account_repo.calculate_balance.return_value = Decimal("100.00")

        dashboard_service.get_net_worth()

        assert mock_account_repo.calculate_balance.call_count == 3


class TestGetMonthlySummary:
    """Tests for DashboardService.get_monthly_summary — validates response shape only."""

    def test_get_monthly_summary_response_shape(
        self, dashboard_service, mock_db
    ):
        """Should return a dict with all required keys for a given month/year."""
        result = dashboard_service.get_monthly_summary(mes=3, anio=2026)

        assert "mes" in result
        assert "anio" in result
        assert "total_ingresos" in result
        assert "total_gastos" in result
        assert "neto" in result
        assert "top_categorias_gasto" in result
        assert "top_categorias_ingreso" in result
        assert result["mes"] == 3
        assert result["anio"] == 2026

    def test_get_monthly_summary_neto_is_ingresos_minus_gastos(
        self, dashboard_service, mock_db
    ):
        """neto must equal total_ingresos minus total_gastos."""
        # mock_db scalar returns Decimal("0") → ingresos=0, gastos=0, neto=0
        result = dashboard_service.get_monthly_summary(mes=1, anio=2026)

        assert result["neto"] == result["total_ingresos"] - result["total_gastos"]

    def test_get_monthly_summary_top_categorias_are_lists(
        self, dashboard_service, mock_db
    ):
        """top_categorias_gasto and top_categorias_ingreso should be lists."""
        result = dashboard_service.get_monthly_summary(mes=6, anio=2025)

        assert isinstance(result["top_categorias_gasto"], list)
        assert isinstance(result["top_categorias_ingreso"], list)


class TestGetRecentActivity:
    """Tests for DashboardService.get_recent_activity."""

    def test_get_recent_activity_combines_transactions_and_transfers(
        self, dashboard_service, mock_transaction_repo, mock_transfer_repo
    ):
        """Should return activities from both transactions and transfers."""
        mock_transaction_repo.get_recent.return_value = [_make_mock_transaction()]
        mock_transfer_repo.get_recent.return_value = [_make_mock_transfer()]

        result = dashboard_service.get_recent_activity(limit=10)

        # At least one of each type should appear
        tipos = {item["tipo"] for item in result}
        assert "transaccion" in tipos
        assert "transferencia" in tipos

    def test_get_recent_activity_empty_repos(
        self, dashboard_service, mock_transaction_repo, mock_transfer_repo
    ):
        """Should return an empty list when there are no transactions or transfers."""
        mock_transaction_repo.get_recent.return_value = []
        mock_transfer_repo.get_recent.return_value = []

        result = dashboard_service.get_recent_activity()

        assert result == []


class TestGetDashboardData:
    """Tests for DashboardService.get_dashboard_data."""

    def test_get_dashboard_data_uses_current_month_year_as_defaults(
        self, dashboard_service, mock_account_repo, mock_transaction_repo,
        mock_transfer_repo, mock_db
    ):
        """Should default mes/anio to the current month/year when not provided."""
        mock_account_repo.get_all_active.return_value = []
        mock_transaction_repo.get_recent.return_value = []
        mock_transfer_repo.get_recent.return_value = []

        result = dashboard_service.get_dashboard_data()

        today = date.today()
        assert result["resumen_mensual"]["mes"] == today.month
        assert result["resumen_mensual"]["anio"] == today.year

    def test_get_dashboard_data_response_contains_all_sections(
        self, dashboard_service, mock_account_repo, mock_transaction_repo,
        mock_transfer_repo, mock_db
    ):
        """Should return a dict with patrimonio_neto, resumen_mensual, actividad_reciente."""
        mock_account_repo.get_all_active.return_value = []
        mock_transaction_repo.get_recent.return_value = []
        mock_transfer_repo.get_recent.return_value = []

        result = dashboard_service.get_dashboard_data(mes=3, anio=2026)

        assert "patrimonio_neto" in result
        assert "resumen_mensual" in result
        assert "actividad_reciente" in result

    def test_get_dashboard_data_passes_explicit_month_year(
        self, dashboard_service, mock_account_repo, mock_transaction_repo,
        mock_transfer_repo, mock_db
    ):
        """Should use the explicitly provided mes/anio rather than today."""
        mock_account_repo.get_all_active.return_value = []
        mock_transaction_repo.get_recent.return_value = []
        mock_transfer_repo.get_recent.return_value = []

        result = dashboard_service.get_dashboard_data(mes=6, anio=2025)

        assert result["resumen_mensual"]["mes"] == 6
        assert result["resumen_mensual"]["anio"] == 2025
