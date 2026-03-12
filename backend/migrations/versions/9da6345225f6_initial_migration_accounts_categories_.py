"""Initial migration: accounts, categories, transactions, transfers

Revision ID: 9da6345225f6
Revises:
Create Date: 2026-01-31 15:55:06.107867

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9da6345225f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('categories',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('type', sa.Enum('INCOME', 'EXPENSE', 'BOTH', name='categorytype'), nullable=False),
    sa.Column('icon', sa.String(length=50), nullable=True),
    sa.Column('color', sa.String(length=7), nullable=True),
    sa.Column('parent_category_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('client_id', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['parent_category_id'], ['categories.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id')
    )
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.create_index('idx_categories_parent', ['parent_category_id'], unique=False)
        batch_op.create_index('idx_categories_type', ['type'], unique=False)
        batch_op.create_index('idx_categories_client_id', ['client_id'], unique=True)

    op.create_table('accounts',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('type', sa.Enum('DEBIT', 'CREDIT', 'CASH', name='accounttype'), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('tags', postgresql.ARRAY(sa.String(length=50)), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('client_id', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id')
    )
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.create_index('idx_accounts_client_id', ['client_id'], unique=True)

    op.create_table('transactions',
    sa.Column('type', sa.Enum('INCOME', 'EXPENSE', name='transactiontype'), nullable=False),
    sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('account_id', sa.UUID(), nullable=False),
    sa.Column('category_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=True),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('tags', postgresql.ARRAY(sa.String(length=50)), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('client_id', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id')
    )
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.create_index('idx_transactions_category', ['category_id'], unique=False)
        batch_op.create_index('idx_transactions_account_date', ['account_id', 'date'], unique=False)
        batch_op.create_index('idx_transactions_account_type', ['account_id', 'type'], unique=False)
        batch_op.create_index('idx_transactions_date', ['date'], unique=False)
        batch_op.create_index('idx_transactions_client_id', ['client_id'], unique=True)

    op.create_table('transfers',
    sa.Column('source_account_id', sa.UUID(), nullable=False),
    sa.Column('destination_account_id', sa.UUID(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('tags', postgresql.ARRAY(sa.String(length=50)), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('client_id', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['destination_account_id'], ['accounts.id'], ),
    sa.ForeignKeyConstraint(['source_account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id')
    )
    with op.batch_alter_table('transfers', schema=None) as batch_op:
        batch_op.create_index('idx_transfers_destination', ['destination_account_id'], unique=False)
        batch_op.create_index('idx_transfers_date', ['date'], unique=False)
        batch_op.create_index('idx_transfers_source', ['source_account_id'], unique=False)
        batch_op.create_index('idx_transfers_client_id', ['client_id'], unique=True)


def downgrade():
    with op.batch_alter_table('transfers', schema=None) as batch_op:
        batch_op.drop_index('idx_transfers_source')
        batch_op.drop_index('idx_transfers_date')
        batch_op.drop_index('idx_transfers_destination')
        batch_op.drop_index('idx_transfers_client_id')

    op.drop_table('transfers')
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_index('idx_transactions_date')
        batch_op.drop_index('idx_transactions_account_type')
        batch_op.drop_index('idx_transactions_account_date')
        batch_op.drop_index('idx_transactions_category')
        batch_op.drop_index('idx_transactions_client_id')

    op.drop_table('transactions')
    op.drop_table('accounts')
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_index('idx_categories_type')
        batch_op.drop_index('idx_categories_parent')
        batch_op.drop_index('idx_categories_client_id')

    op.drop_table('categories')
