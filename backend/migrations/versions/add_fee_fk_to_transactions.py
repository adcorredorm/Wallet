"""add fee FK columns to transactions

Revision ID: d1e2f3a4b5c6
Revises: c3d4e5f6a7b8
Create Date: 2026-03-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'd1e2f3a4b5c6'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'transactions',
        sa.Column(
            'fee_for_transaction_id',
            UUID(as_uuid=True),
            sa.ForeignKey('transactions.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.add_column(
        'transactions',
        sa.Column(
            'fee_for_transfer_id',
            UUID(as_uuid=True),
            sa.ForeignKey('transfers.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.create_index(
        'idx_transactions_fee_for_transaction',
        'transactions',
        ['fee_for_transaction_id'],
    )
    op.create_index(
        'idx_transactions_fee_for_transfer',
        'transactions',
        ['fee_for_transfer_id'],
    )
    op.create_check_constraint(
        'ck_transactions_fee_one_source',
        'transactions',
        '(fee_for_transaction_id IS NULL) OR (fee_for_transfer_id IS NULL)',
    )


def downgrade():
    op.drop_constraint('ck_transactions_fee_one_source', 'transactions', type_='check')
    op.drop_index('idx_transactions_fee_for_transfer', table_name='transactions')
    op.drop_index('idx_transactions_fee_for_transaction', table_name='transactions')
    op.drop_column('transactions', 'fee_for_transfer_id')
    op.drop_column('transactions', 'fee_for_transaction_id')
