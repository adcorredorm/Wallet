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
    account.nombre = "Cuenta Test"
    account.tipo = AccountType.DEBITO
    account.divisa = "MXN"
    account.descripcion = "Descripción de prueba"
    account.tags = ["test", "mock"]
    account.activa = True

    # Mock relationships (dynamic queries)
    # These are configured to not trigger lazy loading
    account.transacciones = MagicMock()
    account.transacciones.count.return_value = 0
    account.transferencias_origen = MagicMock()
    account.transferencias_origen.count.return_value = 0
    account.transferencias_destino = MagicMock()
    account.transferencias_destino.count.return_value = 0

    return account


@pytest.fixture
def mock_account_with_transactions(mock_account):
    """
    Create a mock Account with transactions.

    Returns:
        Mock Account instance with transaction count > 0
    """
    mock_account.transacciones.count.return_value = 5
    return mock_account


@pytest.fixture
def mock_account_with_transfers(mock_account):
    """
    Create a mock Account with transfers.

    Returns:
        Mock Account instance with transfer counts > 0
    """
    mock_account.transferencias_origen.count.return_value = 3
    mock_account.transferencias_destino.count.return_value = 2
    return mock_account


@pytest.fixture
def mock_archived_account(mock_account):
    """
    Create a mock archived Account.

    Returns:
        Mock Account instance with activa=False
    """
    mock_account.activa = False
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
        ("MXN", AccountType.DEBITO),
        ("USD", AccountType.CREDITO),
        ("EUR", AccountType.EFECTIVO),
    ]):
        account = Mock(spec=Account)
        account.id = uuid4()
        account.nombre = f"Cuenta {i+1}"
        account.tipo = account_type
        account.divisa = currency
        account.descripcion = f"Descripción {i+1}"
        account.tags = [f"tag{i+1}"]
        account.activa = True

        # Mock relationships
        account.transacciones = MagicMock()
        account.transacciones.count.return_value = 0
        account.transferencias_origen = MagicMock()
        account.transferencias_origen.count.return_value = 0
        account.transferencias_destino = MagicMock()
        account.transferencias_destino.count.return_value = 0

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
    category.nombre = "Categoría Test"
    category.tipo = CategoryType.GASTO
    category.icono = "test-icon"
    category.color = "#FF5733"
    category.categoria_padre_id = None

    # Mock relationships
    category.subcategorias = MagicMock()
    category.subcategorias.count.return_value = 0
    category.transacciones = MagicMock()
    category.transacciones.count.return_value = 0

    return category


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
        'nombre': 'Test Account',
        'tipo': AccountType.DEBITO,
        'divisa': 'MXN',
        'descripcion': 'Test description',
        'tags': [],
        'activa': True,
    }
    defaults.update(overrides)

    account = Mock(spec=Account)
    for key, value in defaults.items():
        setattr(account, key, value)

    # Mock relationships
    account.transacciones = MagicMock()
    account.transacciones.count.return_value = 0
    account.transferencias_origen = MagicMock()
    account.transferencias_origen.count.return_value = 0
    account.transferencias_destino = MagicMock()
    account.transferencias_destino.count.return_value = 0

    return account
