"""
Unit tests for DashboardService.

These tests focus on business logic validation using mocked repositories
and a patched db.session for methods that bypass the repository layer and
query SQLAlchemy directly.

No real database, no Flask app context — pure unit tests.
All service methods now accept user_id — the tests pass a fixed UUID.
"""

import pytest
from decimal import Decimal
from datetime import date
from uuid import uuid4, UUID
from unittest.mock import Mock, MagicMock, patch

from app.services.dashboard import DashboardService
from app.models.account import Account
from app.models.transaction import Transaction, TransactionType
from app.models.transfer import Transfer


USER_ID = uuid4()


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

def _make_mock_transaction(type: TransactionType = TransactionType.EXPENSE) -> Mock:
    """
    Build a Transaction mock suitable for get_recent_activity.

    The service accesses trans.category.name and trans.account.name when
    formatting recent activity, so those nested attributes must exist.
    """
    trans = MagicMock()
    trans.id = uuid4()
    trans.type = type
    trans.amount = Decimal("100.00")
    trans.date = date(2026, 3, 1)
    trans.title = None  # triggers the fallback description path

    category = Mock()
    category.name = "Categoría test"
    trans.category = category

    account = Mock()
    account.name = "Cuenta test"
    trans.account = account

    return trans


def _make_mock_transfer() -> Mock:
    """
    Build a Transfer mock suitable for get_recent_activity.

    The service accesses transfer.source_account.name and
    transfer.destination_account.name when formatting recent activity.
    """
    transfer = MagicMock()
    transfer.id = uuid4()
    transfer.amount = Decimal("200.00")
    transfer.date = date(2026, 3, 1)
    transfer.description = None  # triggers the fallback description path

    source_account = Mock()
    source_account.name = "Origen test"
    transfer.source_account = source_account

    destination_account = Mock()
    destination_account.name = "Destino test"
    transfer.destination_account = destination_account

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
        account_mxn_1.currency = "MXN"

        account_mxn_2 = MagicMock()
        account_mxn_2.id = uuid4()
        account_mxn_2.currency = "MXN"

        account_usd = MagicMock()
        account_usd.id = uuid4()
        account_usd.currency = "USD"

        mock_account_repo.get_all_active.return_value = [
            account_mxn_1, account_mxn_2, account_usd
        ]
        mock_account_repo.calculate_balance.side_effect = [
            Decimal("1000.00"),
            Decimal("500.00"),
            Decimal("200.00"),
        ]

        result = dashboard_service.get_net_worth(user_id=USER_ID)

        balances = {b["currency"]: b["total"] for b in result["balances"]}
        assert balances["MXN"] == 1500.0  # 1000 + 500
        assert balances["USD"] == 200.0
        assert "calculation_date" in result

    def test_get_net_worth_empty_accounts_returns_empty_balances(
        self, dashboard_service, mock_account_repo
    ):
        """Should return an empty balances list when no active accounts exist."""
        mock_account_repo.get_all_active.return_value = []

        result = dashboard_service.get_net_worth(user_id=USER_ID)

        assert result["balances"] == []
        assert "calculation_date" in result

    def test_get_net_worth_calls_calculate_balance_for_each_account(
        self, dashboard_service, mock_account_repo
    ):
        """Should call calculate_balance once per active account."""
        accounts = [MagicMock(id=uuid4(), currency="MXN") for _ in range(3)]
        mock_account_repo.get_all_active.return_value = accounts
        mock_account_repo.calculate_balance.return_value = Decimal("100.00")

        dashboard_service.get_net_worth(user_id=USER_ID)

        assert mock_account_repo.calculate_balance.call_count == 3


class TestGetMonthlySummary:
    """Tests for DashboardService.get_monthly_summary — validates response shape only."""

    def test_get_monthly_summary_response_shape(
        self, dashboard_service, mock_db
    ):
        """Should return a dict with all required keys for a given month/year."""
        result = dashboard_service.get_monthly_summary(
            user_id=USER_ID, month=3, year=2026
        )

        assert "month" in result
        assert "year" in result
        assert "total_income" in result
        assert "total_expenses" in result
        assert "net" in result
        assert "top_expense_categories" in result
        assert "top_income_categories" in result
        assert result["month"] == 3
        assert result["year"] == 2026

    def test_get_monthly_summary_net_is_income_minus_expenses(
        self, dashboard_service, mock_db
    ):
        """net must equal total_income minus total_expenses."""
        result = dashboard_service.get_monthly_summary(
            user_id=USER_ID, month=1, year=2026
        )

        assert result["net"] == result["total_income"] - result["total_expenses"]

    def test_get_monthly_summary_top_categories_are_lists(
        self, dashboard_service, mock_db
    ):
        """top_expense_categories and top_income_categories should be lists."""
        result = dashboard_service.get_monthly_summary(
            user_id=USER_ID, month=6, year=2025
        )

        assert isinstance(result["top_expense_categories"], list)
        assert isinstance(result["top_income_categories"], list)


class TestGetRecentActivity:
    """Tests for DashboardService.get_recent_activity."""

    def test_get_recent_activity_combines_transactions_and_transfers(
        self, dashboard_service, mock_transaction_repo, mock_transfer_repo
    ):
        """Should return activities from both transactions and transfers."""
        mock_transaction_repo.get_recent.return_value = [_make_mock_transaction()]
        mock_transfer_repo.get_recent.return_value = [_make_mock_transfer()]

        result = dashboard_service.get_recent_activity(user_id=USER_ID, limit=10)

        types = {item["type"] for item in result}
        assert "transaction" in types
        assert "transfer" in types

    def test_get_recent_activity_empty_repos(
        self, dashboard_service, mock_transaction_repo, mock_transfer_repo
    ):
        """Should return an empty list when there are no transactions or transfers."""
        mock_transaction_repo.get_recent.return_value = []
        mock_transfer_repo.get_recent.return_value = []

        result = dashboard_service.get_recent_activity(user_id=USER_ID)

        assert result == []


class TestGetDashboardData:
    """Tests for DashboardService.get_dashboard_data."""

    def test_get_dashboard_data_uses_current_month_year_as_defaults(
        self, dashboard_service, mock_account_repo, mock_transaction_repo,
        mock_transfer_repo, mock_db
    ):
        """Should default month/year to the current month/year when not provided."""
        mock_account_repo.get_all_active.return_value = []
        mock_transaction_repo.get_recent.return_value = []
        mock_transfer_repo.get_recent.return_value = []

        result = dashboard_service.get_dashboard_data(user_id=USER_ID)

        today = date.today()
        assert result["monthly_summary"]["month"] == today.month
        assert result["monthly_summary"]["year"] == today.year

    def test_get_dashboard_data_response_contains_all_sections(
        self, dashboard_service, mock_account_repo, mock_transaction_repo,
        mock_transfer_repo, mock_db
    ):
        """Should return a dict with net_worth, monthly_summary, recent_activity."""
        mock_account_repo.get_all_active.return_value = []
        mock_transaction_repo.get_recent.return_value = []
        mock_transfer_repo.get_recent.return_value = []

        result = dashboard_service.get_dashboard_data(user_id=USER_ID, month=3, year=2026)

        assert "net_worth" in result
        assert "monthly_summary" in result
        assert "recent_activity" in result

    def test_get_dashboard_data_passes_explicit_month_year(
        self, dashboard_service, mock_account_repo, mock_transaction_repo,
        mock_transfer_repo, mock_db
    ):
        """Should use the explicitly provided month/year rather than today."""
        mock_account_repo.get_all_active.return_value = []
        mock_transaction_repo.get_recent.return_value = []
        mock_transfer_repo.get_recent.return_value = []

        result = dashboard_service.get_dashboard_data(user_id=USER_ID, month=6, year=2025)

        assert result["monthly_summary"]["month"] == 6
        assert result["monthly_summary"]["year"] == 2025
