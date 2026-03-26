"""add superseded_at to refresh_tokens

Revision ID: c4a38322e31e
Revises: 57e28a578ee7
Create Date: 2026-03-26 14:53:40.768513

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4a38322e31e'
down_revision = '57e28a578ee7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('superseded_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.drop_column('superseded_at')
