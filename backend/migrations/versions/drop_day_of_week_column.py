"""drop day_of_week from recurring_rules

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-29 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'recurring_rules' AND column_name = 'day_of_week'"
    ))
    if result.fetchone():
        op.drop_column('recurring_rules', 'day_of_week')


def downgrade():
    op.add_column('recurring_rules', sa.Column('day_of_week', sa.Integer(), nullable=True))
