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
