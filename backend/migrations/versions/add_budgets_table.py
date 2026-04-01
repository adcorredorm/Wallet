"""add budgets table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-03-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'budgets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('offline_id', sa.String(100), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=True),
        sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='CASCADE'), nullable=True),
        sa.Column('amount_limit', sa.Numeric(20, 8), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('budget_type', sa.Enum('recurring', 'one_time', name='budgettype'), nullable=False),
        sa.Column('frequency', sa.Enum('daily', 'weekly', 'monthly', 'yearly', name='budgetfrequency'), nullable=True),
        sa.Column('interval', sa.Integer(), nullable=True),
        sa.Column('reference_date', sa.Date(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('active', 'paused', 'archived', name='budgetstatus'), nullable=False, server_default='active'),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(7), nullable=True),
        sa.CheckConstraint(
            "(account_id IS NULL) != (category_id IS NULL)",
            name="ck_budget_scope_xor",
        ),
    )
    op.create_index('idx_budgets_user_status', 'budgets', ['user_id', 'status'])
    op.create_index('idx_budgets_account', 'budgets', ['account_id'])
    op.create_index('idx_budgets_category', 'budgets', ['category_id'])
    op.create_unique_constraint('uq_budgets_user_offline', 'budgets', ['user_id', 'offline_id'])


def downgrade():
    op.drop_table('budgets')
    op.execute("DROP TYPE IF EXISTS budgettype")
    op.execute("DROP TYPE IF EXISTS budgetfrequency")
    op.execute("DROP TYPE IF EXISTS budgetstatus")
