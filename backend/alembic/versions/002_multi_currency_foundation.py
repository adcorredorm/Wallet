"""Multi-currency foundation: ExchangeRate + UserSetting tables, higher-precision amounts

Revision ID: 002_multi_currency_foundation
Revises: 001_initial_schema
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_multi_currency_foundation'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create exchange_rates table
    op.create_table(
        'exchange_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', sa.String(100), nullable=True, unique=True),
        sa.Column('currency_code', sa.String(10), nullable=False),
        sa.Column('rate_to_usd', sa.Numeric(20, 10), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('fetched_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index(
        'idx_exchange_rates_currency_code',
        'exchange_rates',
        ['currency_code'],
        unique=True,
    )
    op.create_index(
        'idx_exchange_rates_client_id',
        'exchange_rates',
        ['client_id'],
        unique=True,
    )

    # Create user_settings table
    op.create_table(
        'user_settings',
        sa.Column('key', sa.String(100), primary_key=True, nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    # Alter transactions.amount: NUMERIC(15,2) -> NUMERIC(20,8)
    op.alter_column(
        'transactions',
        'amount',
        existing_type=sa.Numeric(15, 2),
        type_=sa.Numeric(20, 8),
        existing_nullable=False,
    )

    # Alter transfers.amount: NUMERIC(15,2) -> NUMERIC(20,8)
    op.alter_column(
        'transfers',
        'amount',
        existing_type=sa.Numeric(15, 2),
        type_=sa.Numeric(20, 8),
        existing_nullable=False,
    )

    # Seed USD baseline exchange rate
    op.execute(
        """
        INSERT INTO exchange_rates (id, currency_code, rate_to_usd, source, fetched_at, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'USD',
            1.0,
            'system',
            NOW(),
            NOW(),
            NOW()
        )
        """
    )

    # Seed primary_currency setting
    op.execute(
        """
        INSERT INTO user_settings (key, value, updated_at)
        VALUES ('primary_currency', '"COP"', NOW())
        """
    )


def downgrade() -> None:
    # Revert transfers.amount: NUMERIC(20,8) -> NUMERIC(15,2)
    op.alter_column(
        'transfers',
        'amount',
        existing_type=sa.Numeric(20, 8),
        type_=sa.Numeric(15, 2),
        existing_nullable=False,
    )

    # Revert transactions.amount: NUMERIC(20,8) -> NUMERIC(15,2)
    op.alter_column(
        'transactions',
        'amount',
        existing_type=sa.Numeric(20, 8),
        type_=sa.Numeric(15, 2),
        existing_nullable=False,
    )

    # Drop user_settings table
    op.drop_table('user_settings')

    # Drop exchange_rates table (indexes are dropped automatically with the table)
    op.drop_index('idx_exchange_rates_client_id', table_name='exchange_rates')
    op.drop_index('idx_exchange_rates_currency_code', table_name='exchange_rates')
    op.drop_table('exchange_rates')
