"""Transactions multi-currency: add original_amount, original_currency, exchange_rate

Revision ID: 004_transactions_multi_currency
Revises: 003_transfers_cross_currency
Create Date: 2026-03-12

Adds three nullable columns to the transactions table to capture the original
currency context when a transaction is recorded in a currency different from the
account's primary currency. Existing single-currency transactions are left as
NULL — no backfill needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_transactions_multi_currency'
down_revision: Union[str, None] = '003_transfers_cross_currency'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add original_amount: the amount in the original transaction currency
    op.add_column(
        'transactions',
        sa.Column('original_amount', sa.Numeric(20, 8), nullable=True),
    )

    # Add original_currency: ISO 4217 currency code of the original transaction currency
    op.add_column(
        'transactions',
        sa.Column('original_currency', sa.String(10), nullable=True),
    )

    # Add exchange_rate: rate applied at transaction time (original currency / account currency)
    op.add_column(
        'transactions',
        sa.Column('exchange_rate', sa.Numeric(20, 10), nullable=True),
    )


def downgrade() -> None:
    # Drop in reverse order of addition
    op.drop_column('transactions', 'exchange_rate')
    op.drop_column('transactions', 'original_currency')
    op.drop_column('transactions', 'original_amount')
