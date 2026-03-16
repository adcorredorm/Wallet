"""Tests verifying all domain models have user_id FK and composite offline_id constraint."""
import pytest
from sqlalchemy import UniqueConstraint

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.dashboard import Dashboard
from app.models.dashboard_widget import DashboardWidget


DOMAIN_MODELS = [Account, Category, Transaction, Transfer, Dashboard, DashboardWidget]
DOMAIN_NAMES = ["Account", "Category", "Transaction", "Transfer", "Dashboard", "DashboardWidget"]


@pytest.mark.parametrize("model,name", list(zip(DOMAIN_MODELS, DOMAIN_NAMES)))
def test_domain_model_has_user_id_column(app, model, name):
    """All domain models must have a user_id column."""
    columns = {c.name for c in model.__table__.columns}
    assert "user_id" in columns, f"{name} is missing user_id column"


@pytest.mark.parametrize("model,name", list(zip(DOMAIN_MODELS, DOMAIN_NAMES)))
def test_domain_model_user_id_fk_to_users(app, model, name):
    """user_id must be a FK to users.id."""
    fk_tables = {fk.column.table.name for fk in model.__table__.foreign_keys}
    assert "users" in fk_tables, f"{name}.user_id is not a FK to users table"


@pytest.mark.parametrize("model,name", list(zip(DOMAIN_MODELS, DOMAIN_NAMES)))
def test_domain_model_has_composite_offline_id_constraint(app, model, name):
    """All domain models must have a composite UniqueConstraint on (user_id, offline_id)."""
    unique_constraints = [
        c for c in model.__table__.constraints
        if isinstance(c, UniqueConstraint)
    ]
    composite_found = any(
        set(col.name for col in uc.columns) == {"user_id", "offline_id"}
        for uc in unique_constraints
    )
    assert composite_found, (
        f"{name} is missing composite UniqueConstraint on (user_id, offline_id)"
    )


@pytest.mark.parametrize("model,name", list(zip(DOMAIN_MODELS, DOMAIN_NAMES)))
def test_domain_model_offline_id_has_no_table_wide_unique(app, model, name):
    """offline_id must NOT have a standalone table-wide UNIQUE constraint."""
    unique_constraints = [
        c for c in model.__table__.constraints
        if isinstance(c, UniqueConstraint)
    ]
    solo_offline_id_unique = any(
        {col.name for col in uc.columns} == {"offline_id"}
        for uc in unique_constraints
    )
    assert not solo_offline_id_unique, (
        f"{name} still has a standalone UNIQUE constraint on offline_id"
    )
