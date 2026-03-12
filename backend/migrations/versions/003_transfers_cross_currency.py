"""Transfers cross-currency: add destination_amount, exchange_rate, destination_currency

Revision ID: 003_transfers_cross_currency
Revises: 002_multi_currency_foundation
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '003_transfers_cross_currency'
down_revision: Union[str, None] = '002_multi_currency_foundation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transfers', sa.Column('destination_amount', sa.Numeric(20, 8), nullable=True))
    op.add_column('transfers', sa.Column('exchange_rate', sa.Numeric(20, 10), nullable=True))
    op.add_column('transfers', sa.Column('destination_currency', sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column('transfers', 'destination_currency')
    op.drop_column('transfers', 'exchange_rate')
    op.drop_column('transfers', 'destination_amount')
