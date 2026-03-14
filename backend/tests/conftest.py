"""
Pytest configuration and fixtures.

This module provides common fixtures and configuration for all tests.
"""

import pytest
from unittest.mock import Mock, MagicMock
from decimal import Decimal
from uuid import uuid4

from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionType
from app.models.category import Category, CategoryType


# ============================================================================
# APP FIXTURES (for integration tests)
# ============================================================================

@pytest.fixture
def app():
    """
    Create and configure a test Flask application instance.

    This fixture is for integration tests that need a real Flask app.

    Yields:
        Flask application configured for testing
    """
    from app import create_app
    from app.extensions import db

    app = create_app("testing")

    with app.app_context():
        # Create all tables
        db.create_all()

        yield app

        # Cleanup
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """
    Create a test client for the Flask application.

    Args:
        app: Flask application fixture

    Returns:
        Flask test client
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    Create a test CLI runner.

    Args:
        app: Flask application fixture

    Returns:
        Flask CLI test runner
    """
    return app.test_cli_runner()


@pytest.fixture
def db_session(app):
    """
    Create a database session for tests.

    Args:
        app: Flask application fixture

    Yields:
        SQLAlchemy database session
    """
    from app.extensions import db
    with app.app_context():
        yield db.session


# ============================================================================
# MOCK DATA FIXTURES (for unit tests)
# ============================================================================

@pytest.fixture
def mock_account_id():
    """Generate a mock UUID for accounts."""
    return uuid4()


@pytest.fixture
def mock_account(mock_account_id):
    """
    Create a mock Account instance.

    This mock has all the attributes of a real Account but doesn't require
    database connection or app context.

    Returns:
        Mock Account instance with typical attributes
    """
    account = Mock(spec=Account)
    account.id = mock_account_id
    account.name = "Cuenta Test"
    account.type = AccountType.DEBIT
    account.currency = "MXN"
    account.description = "Descripción de prueba"
    account.tags = ["test", "mock"]
    account.active = True

    # Mock relationships (dynamic queries)
    # These are configured to not trigger lazy loading
    account.transactions = MagicMock()
    account.transactions.count.return_value = 0
    account.transfers_source = MagicMock()
    account.transfers_source.count.return_value = 0
    account.transfers_destination = MagicMock()
    account.transfers_destination.count.return_value = 0

    return account


@pytest.fixture
def mock_account_with_transactions(mock_account):
    """
    Create a mock Account with transactions.

    Returns:
        Mock Account instance with transaction count > 0
    """
    mock_account.transactions.count.return_value = 5
    return mock_account


@pytest.fixture
def mock_account_with_transfers(mock_account):
    """
    Create a mock Account with transfers.

    Returns:
        Mock Account instance with transfer counts > 0
    """
    mock_account.transfers_source.count.return_value = 3
    mock_account.transfers_destination.count.return_value = 2
    return mock_account


@pytest.fixture
def mock_archived_account(mock_account):
    """
    Create a mock archived Account.

    Returns:
        Mock Account instance with active=False
    """
    mock_account.active = False
    return mock_account


@pytest.fixture
def multiple_mock_accounts():
    """
    Create multiple mock accounts for list operations.

    Returns:
        List of 3 mock Account instances with different currencies
    """
    accounts = []
    for i, (currency, account_type) in enumerate([
        ("MXN", AccountType.DEBIT),
        ("USD", AccountType.CREDIT),
        ("EUR", AccountType.CASH),
    ]):
        account = Mock(spec=Account)
        account.id = uuid4()
        account.name = f"Cuenta {i+1}"
        account.type = account_type
        account.currency = currency
        account.description = f"Descripción {i+1}"
        account.tags = [f"tag{i+1}"]
        account.active = True

        # Mock relationships
        account.transactions = MagicMock()
        account.transactions.count.return_value = 0
        account.transfers_source = MagicMock()
        account.transfers_source.count.return_value = 0
        account.transfers_destination = MagicMock()
        account.transfers_destination.count.return_value = 0

        accounts.append(account)

    return accounts


# ============================================================================
# CATEGORY FIXTURES
# ============================================================================

@pytest.fixture
def mock_category():
    """Create a mock Category instance."""
    category = Mock(spec=Category)
    category.id = uuid4()
    category.name = "Categoría Test"
    category.type = CategoryType.EXPENSE
    category.icon = "test-icon"
    category.color = "#FF5733"
    category.parent_category_id = None

    # Mock relationships
    category.subcategories = MagicMock()
    category.subcategories.count.return_value = 0
    category.transactions = MagicMock()
    category.transactions.count.return_value = 0

    return category


# ============================================================================
# TRANSFER FIXTURES
# ============================================================================

@pytest.fixture
def mock_transfer():
    """
    Create a mock Transfer instance.

    Returns:
        Mock Transfer instance with typical attributes
    """
    from datetime import date
    from decimal import Decimal

    transfer = MagicMock()
    transfer.id = uuid4()
    transfer.source_account_id = uuid4()
    transfer.destination_account_id = uuid4()
    transfer.amount = Decimal("500.00")
    transfer.date = date(2026, 3, 1)
    transfer.description = "Transferencia test"
    transfer.tags = ["test"]
    transfer.client_id = None
    transfer.base_rate = None
    return transfer


# ============================================================================
# TRANSACTION FIXTURES
# ============================================================================

@pytest.fixture
def mock_transaction():
    """
    Create a mock Transaction instance.

    Returns:
        Mock Transaction instance with typical attributes
    """
    from app.models.transaction import TransactionType

    transaction = MagicMock()
    transaction.id = uuid4()
    transaction.type = TransactionType.EXPENSE
    transaction.amount = Decimal("250.00")
    from datetime import date
    transaction.date = date(2026, 3, 1)
    transaction.account_id = uuid4()
    transaction.category_id = uuid4()
    transaction.title = "Compra test"
    transaction.description = "Descripción test"
    transaction.tags = ["test"]
    transaction.client_id = None
    transaction.base_rate = None
    return transaction


# ============================================================================
# DECIMAL/BALANCE FIXTURES
# ============================================================================

@pytest.fixture
def mock_balance():
    """Return a typical balance value."""
    return Decimal("1500.50")


@pytest.fixture
def zero_balance():
    """Return a zero balance."""
    return Decimal("0.00")


@pytest.fixture
def negative_balance():
    """Return a negative balance."""
    return Decimal("-250.75")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_mock_account(**overrides):
    """
    Helper function to create mock accounts with custom attributes.

    Args:
        **overrides: Attributes to override in the mock account

    Returns:
        Mock Account instance
    """
    defaults = {
        'id': uuid4(),
        'name': 'Test Account',
        'type': AccountType.DEBIT,
        'currency': 'MXN',
        'description': 'Test description',
        'tags': [],
        'active': True,
    }
    defaults.update(overrides)

    account = Mock(spec=Account)
    for key, value in defaults.items():
        setattr(account, key, value)

    # Mock relationships
    account.transactions = MagicMock()
    account.transactions.count.return_value = 0
    account.transfers_source = MagicMock()
    account.transfers_source.count.return_value = 0
    account.transfers_destination = MagicMock()
    account.transfers_destination.count.return_value = 0

    return account


# ============================================================================
# REAL DB FACTORY FIXTURES (para integration y repository tests)
# ============================================================================

@pytest.fixture
def make_account(app):
    """Factory que crea Account reales en DB.
    NO usar with app.app_context() — el fixture `app` ya activa el contexto.
    """
    from app.extensions import db
    from app.models.account import Account, AccountType
    from uuid import uuid4

    def _make(**kwargs):
        defaults = dict(
            name=f"Cuenta {uuid4().hex[:6]}",
            type=AccountType.DEBIT,
            currency="MXN",
            active=True,
        )
        defaults.update(kwargs)
        account = Account(**defaults)
        db.session.add(account)
        db.session.commit()
        db.session.refresh(account)
        return account
    yield _make


@pytest.fixture
def make_category(app):
    """Factory que crea Category reales en DB."""
    from app.extensions import db
    from app.models.category import Category, CategoryType
    from uuid import uuid4

    def _make(**kwargs):
        defaults = dict(
            name=f"Cat {uuid4().hex[:6]}",
            type=CategoryType.EXPENSE,
            active=True,
        )
        defaults.update(kwargs)
        cat = Category(**defaults)
        db.session.add(cat)
        db.session.commit()
        db.session.refresh(cat)
        return cat
    yield _make


@pytest.fixture
def make_dashboard(app):
    """Factory que crea Dashboard reales en DB.
    display_currency es nullable=False — siempre proveer un valor.
    """
    from app.extensions import db
    from app.models.dashboard import Dashboard
    from uuid import uuid4

    def _make(**kwargs):
        defaults = dict(
            name=f"Dashboard {uuid4().hex[:6]}",
            is_default=False,
            sort_order=0,
            display_currency="USD",
        )
        defaults.update(kwargs)
        d = Dashboard(**defaults)
        db.session.add(d)
        db.session.commit()
        db.session.refresh(d)
        return d
    yield _make


@pytest.fixture
def make_widget(app):
    """Factory que crea DashboardWidget reales en DB."""
    from app.extensions import db
    from app.models.dashboard_widget import DashboardWidget, WidgetType
    from uuid import uuid4

    def _make(dashboard_id, **kwargs):
        defaults = dict(
            dashboard_id=dashboard_id,
            widget_type=WidgetType.LINE,
            title=f"Widget {uuid4().hex[:6]}",
            position_x=0,
            position_y=0,
            width=4,
            height=2,
            config={},
        )
        defaults.update(kwargs)
        w = DashboardWidget(**defaults)
        db.session.add(w)
        db.session.commit()
        db.session.refresh(w)
        return w
    yield _make


@pytest.fixture
def make_exchange_rate(app):
    """Factory que crea ExchangeRate reales en DB."""
    from app.extensions import db
    from app.models.exchange_rate import ExchangeRate
    from decimal import Decimal
    from datetime import datetime
    from uuid import uuid4

    def _make(currency_code=None, **kwargs):
        code = currency_code or f"T{uuid4().hex[:3].upper()}"
        defaults = dict(
            currency_code=code,
            rate_to_usd=Decimal("1.0"),
            source="test",
            fetched_at=datetime.utcnow(),
        )
        defaults.update(kwargs)
        er = ExchangeRate(**defaults)
        db.session.add(er)
        db.session.commit()
        db.session.refresh(er)
        return er
    yield _make


@pytest.fixture
def make_transaction(app, make_account, make_category):
    """Factory que crea Transaction reales en DB."""
    from app.extensions import db
    from app.models.transaction import Transaction, TransactionType
    from decimal import Decimal
    from datetime import date

    def _make(**kwargs):
        if "account_id" not in kwargs:
            kwargs["account_id"] = make_account().id
        if "category_id" not in kwargs:
            kwargs["category_id"] = make_category().id
        defaults = dict(
            type=TransactionType.EXPENSE,
            amount=Decimal("100.00"),
            date=date.today(),
            title="Test transaction",
        )
        defaults.update(kwargs)
        t = Transaction(**defaults)
        db.session.add(t)
        db.session.commit()
        db.session.refresh(t)
        return t
    yield _make


@pytest.fixture
def make_transfer(app, make_account):
    """Factory que crea Transfer reales en DB."""
    from app.extensions import db
    from app.models.transfer import Transfer
    from decimal import Decimal
    from datetime import date

    def _make(**kwargs):
        if "source_account_id" not in kwargs:
            kwargs["source_account_id"] = make_account().id
        if "destination_account_id" not in kwargs:
            kwargs["destination_account_id"] = make_account().id
        defaults = dict(
            amount=Decimal("50.00"),
            date=date.today(),
        )
        defaults.update(kwargs)
        t = Transfer(**defaults)
        db.session.add(t)
        db.session.commit()
        db.session.refresh(t)
        return t
    yield _make
