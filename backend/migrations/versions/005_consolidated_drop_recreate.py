"""Consolidated drop-and-recreate with base_rate on transactions and transfers.

Revision ID: 005_consolidated_drop_recreate
Revises:
Create Date: 2026-03-12

This migration replaces the prior 4-step chain with a single drop-and-recreate
that delivers the final schema including base_rate on both tables.
All data is test data; no backfill is performed.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_consolidated_drop_recreate"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Drop tables in FK-safe order (children before parents).
    # Use CASCADE so we don't have to enumerate every FK constraint.
    # IF EXISTS makes this safe on a blank database too.
    # ------------------------------------------------------------------
    op.execute("DROP TABLE IF EXISTS transfers CASCADE")
    op.execute("DROP TABLE IF EXISTS transactions CASCADE")
    op.execute("DROP TABLE IF EXISTS accounts CASCADE")
    op.execute("DROP TABLE IF EXISTS exchange_rates CASCADE")
    op.execute("DROP TABLE IF EXISTS user_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS categories CASCADE")

    # Drop custom ENUM types left behind by the old initial migration.
    # Must happen after tables are gone.
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS accounttype")
    op.execute("DROP TYPE IF EXISTS categorytype")

    # ------------------------------------------------------------------
    # Recreate: categories (self-referential FK — must exist before
    # accounts and transactions reference it)
    # ------------------------------------------------------------------
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", sa.String(100), nullable=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column(
            "type",
            sa.Enum("INCOME", "EXPENSE", "BOTH", name="categorytype"),
            nullable=False,
        ),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("parent_category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_index("idx_categories_parent", "categories", ["parent_category_id"])
    op.create_index("idx_categories_type", "categories", ["type"])
    op.create_index("idx_categories_client_id", "categories", ["client_id"], unique=True)

    # ------------------------------------------------------------------
    # Recreate: accounts
    # ------------------------------------------------------------------
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", sa.String(100), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "type",
            sa.Enum("DEBIT", "CREDIT", "CASH", name="accounttype"),
            nullable=False,
        ),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(50)), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_index("idx_accounts_client_id", "accounts", ["client_id"], unique=True)

    # ------------------------------------------------------------------
    # Recreate: transactions (FK -> accounts, categories)
    # Includes base_rate — new in this consolidated migration.
    # ------------------------------------------------------------------
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", sa.String(100), nullable=True),
        sa.Column(
            "type",
            sa.Enum("INCOME", "EXPENSE", name="transactiontype"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(100), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(50)), nullable=False),
        sa.Column("original_amount", sa.Numeric(20, 8), nullable=True),
        sa.Column("original_currency", sa.String(10), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(20, 10), nullable=True),
        sa.Column("base_rate", sa.Numeric(20, 10), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_index("idx_transactions_account_date", "transactions", ["account_id", "date"])
    op.create_index("idx_transactions_account_type", "transactions", ["account_id", "type"])
    op.create_index("idx_transactions_category", "transactions", ["category_id"])
    op.create_index("idx_transactions_date", "transactions", ["date"])
    op.create_index("idx_transactions_client_id", "transactions", ["client_id"], unique=True)

    # ------------------------------------------------------------------
    # Recreate: transfers (FK -> accounts x2)
    # Includes base_rate — new in this consolidated migration.
    # ------------------------------------------------------------------
    op.create_table(
        "transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", sa.String(100), nullable=True),
        sa.Column("source_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(50)), nullable=False),
        sa.Column("destination_amount", sa.Numeric(20, 8), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(20, 10), nullable=True),
        sa.Column("destination_currency", sa.String(10), nullable=True),
        sa.Column("base_rate", sa.Numeric(20, 10), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["destination_account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_index("idx_transfers_source", "transfers", ["source_account_id"])
    op.create_index("idx_transfers_destination", "transfers", ["destination_account_id"])
    op.create_index("idx_transfers_date", "transfers", ["date"])
    op.create_index("idx_transfers_client_id", "transfers", ["client_id"], unique=True)

    # ------------------------------------------------------------------
    # Recreate: exchange_rates (standalone)
    # ------------------------------------------------------------------
    op.create_table(
        "exchange_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", sa.String(100), nullable=True),
        sa.Column("currency_code", sa.String(10), nullable=False),
        sa.Column("rate_to_usd", sa.Numeric(20, 10), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_exchange_rates_currency_code",
        "exchange_rates",
        ["currency_code"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # Recreate: user_settings (standalone)
    # ------------------------------------------------------------------
    op.create_table(
        "user_settings",
        sa.Column("key", sa.String(100), primary_key=True, nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO exchange_rates
            (id, currency_code, rate_to_usd, source, fetched_at, created_at, updated_at)
        VALUES (
            gen_random_uuid(), 'USD', 1.0, 'system', NOW(), NOW(), NOW()
        )
        """
    )
    op.execute(
        """
        INSERT INTO user_settings (key, value, updated_at)
        VALUES ('primary_currency', '"COP"', NOW())
        """
    )


def downgrade() -> None:
    # Full teardown — drop everything in FK-safe order
    op.execute("DROP TABLE IF EXISTS transfers CASCADE")
    op.execute("DROP TABLE IF EXISTS transactions CASCADE")
    op.execute("DROP TABLE IF EXISTS accounts CASCADE")
    op.execute("DROP TABLE IF EXISTS exchange_rates CASCADE")
    op.execute("DROP TABLE IF EXISTS user_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS categories CASCADE")
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS accounttype")
    op.execute("DROP TYPE IF EXISTS categorytype")
