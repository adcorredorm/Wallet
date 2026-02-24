"""Add client_id column to all main tables for offline-first idempotency

Revision ID: a1b2c3d4e5f6
Revises: 9da6345225f6
Create Date: 2026-02-23 00:00:00.000000

Adds an optional client_id VARCHAR(100) column with a UNIQUE constraint to the
four main entity tables (cuentas, transacciones, transferencias, categorias).

The column allows mobile/offline clients to attach a client-generated UUID to
creation requests. When a request is retried after a lost response the server
can detect the duplicate client_id and return the existing record rather than
creating a second one.

Upgrade:  adds client_id + unique index on each table
Downgrade: drops the unique index and the column from each table
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "9da6345225f6"
branch_labels = None
depends_on = None

# Tables that receive the new column
_TABLES = [
    "cuentas",
    "transacciones",
    "transferencias",
    "categorias",
]


def upgrade() -> None:
    """Add client_id VARCHAR(100) NULLABLE UNIQUE to all main entity tables."""
    for table in _TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "client_id",
                    sa.String(length=100),
                    nullable=True,
                )
            )
            batch_op.create_unique_constraint(
                f"uq_{table}_client_id",
                ["client_id"],
            )
            batch_op.create_index(
                f"idx_{table}_client_id",
                ["client_id"],
                unique=True,
            )


def downgrade() -> None:
    """Remove client_id column and its constraints from all main entity tables."""
    for table in reversed(_TABLES):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_index(f"idx_{table}_client_id")
            batch_op.drop_constraint(f"uq_{table}_client_id", type_="unique")
            batch_op.drop_column("client_id")
