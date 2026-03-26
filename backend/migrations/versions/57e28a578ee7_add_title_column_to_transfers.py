"""add title column to transfers

Revision ID: 57e28a578ee7
Revises: 009_rename_offline_id
Create Date: 2026-03-26 08:45:54.029995

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '57e28a578ee7'
down_revision = '009_rename_offline_id'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('transfers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table('transfers', schema=None) as batch_op:
        batch_op.drop_column('title')
