"""add_sort_order_icon_to_accounts

Revision ID: 9135c3a6f6c0
Revises: c4a38322e31e
Create Date: 2026-03-27 03:18:13.863302

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9135c3a6f6c0'
down_revision = 'c4a38322e31e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('accounts', sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('accounts', sa.Column('icon', sa.String(length=50), nullable=True))

    # Backfill sort_order: sequential per user, ordered by created_at (0-based)
    op.execute("""
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) - 1 AS pos
            FROM accounts
        )
        UPDATE accounts SET sort_order = ranked.pos FROM ranked WHERE accounts.id = ranked.id
    """)

    # Backfill icon: default emoji per account type
    op.execute("UPDATE accounts SET icon = '💳' WHERE type IN ('DEBIT', 'CREDIT') AND icon IS NULL")
    op.execute("UPDATE accounts SET icon = '💵' WHERE type = 'CASH' AND icon IS NULL")


def downgrade():
    op.drop_column('accounts', 'icon')
    op.drop_column('accounts', 'sort_order')
