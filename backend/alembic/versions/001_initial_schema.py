"""Initial database schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE accounttype AS ENUM ('debit', 'credit', 'cash')")
    op.execute("CREATE TYPE categorytype AS ENUM ('income', 'expense', 'both')")
    op.execute("CREATE TYPE transactiontype AS ENUM ('income', 'expense')")

    # Create accounts table
    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', sa.String(100), nullable=True, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', postgresql.ENUM('debit', 'credit', 'cash', name='accounttype'), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('idx_accounts_active', 'accounts', ['active'])
    op.create_index('idx_accounts_currency', 'accounts', ['currency'])
    op.create_index('idx_accounts_client_id', 'accounts', ['client_id'], unique=True)

    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', sa.String(100), nullable=True, unique=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('type', postgresql.ENUM('income', 'expense', 'both', name='categorytype'), nullable=False),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('parent_category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('idx_categories_type', 'categories', ['type'])
    op.create_index('idx_categories_parent', 'categories', ['parent_category_id'])
    op.create_index('idx_categories_client_id', 'categories', ['client_id'], unique=True)

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', sa.String(100), nullable=True, unique=True),
        sa.Column('type', postgresql.ENUM('income', 'expense', name='transactiontype'), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id'), nullable=False),
        sa.Column('title', sa.String(100), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('idx_transactions_account_date', 'transactions', ['account_id', 'date'])
    op.create_index('idx_transactions_account_type', 'transactions', ['account_id', 'type'])
    op.create_index('idx_transactions_category', 'transactions', ['category_id'])
    op.create_index('idx_transactions_date', 'transactions', ['date'])
    op.create_index('idx_transactions_client_id', 'transactions', ['client_id'], unique=True)

    # Create transfers table
    op.create_table(
        'transfers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', sa.String(100), nullable=True, unique=True),
        sa.Column('source_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('destination_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('idx_transfers_source', 'transfers', ['source_account_id'])
    op.create_index('idx_transfers_destination', 'transfers', ['destination_account_id'])
    op.create_index('idx_transfers_date', 'transfers', ['date'])
    op.create_index('idx_transfers_client_id', 'transfers', ['client_id'], unique=True)


def downgrade() -> None:
    # Drop tables
    op.drop_table('transfers')
    op.drop_table('transactions')
    op.drop_table('categories')
    op.drop_table('accounts')

    # Drop enum types
    op.execute('DROP TYPE transactiontype')
    op.execute('DROP TYPE categorytype')
    op.execute('DROP TYPE accounttype')
