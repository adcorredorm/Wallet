"""fix recurring enum values to lowercase

Revision ID: a1b2c3d4e5f6
Revises: 2c7f9c3fdbaa
Create Date: 2026-03-29 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '2c7f9c3fdbaa'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Rename recurringfrequency enum values from UPPERCASE to lowercase
    for old, new in [('DAILY', 'daily'), ('WEEKLY', 'weekly'), ('MONTHLY', 'monthly'), ('YEARLY', 'yearly')]:
        bind.execute(sa.text(f"ALTER TYPE recurringfrequency RENAME VALUE '{old}' TO '{new}'"))

    # Rename recurringrulestatus enum values from UPPERCASE to lowercase
    for old, new in [('ACTIVE', 'active'), ('PAUSED', 'paused'), ('COMPLETED', 'completed')]:
        bind.execute(sa.text(f"ALTER TYPE recurringrulestatus RENAME VALUE '{old}' TO '{new}'"))


def downgrade():
    bind = op.get_bind()

    for old, new in [('daily', 'DAILY'), ('weekly', 'WEEKLY'), ('monthly', 'MONTHLY'), ('yearly', 'YEARLY')]:
        bind.execute(sa.text(f"ALTER TYPE recurringfrequency RENAME VALUE '{old}' TO '{new}'"))

    for old, new in [('active', 'ACTIVE'), ('paused', 'PAUSED'), ('completed', 'COMPLETED')]:
        bind.execute(sa.text(f"ALTER TYPE recurringrulestatus RENAME VALUE '{old}' TO '{new}'"))
