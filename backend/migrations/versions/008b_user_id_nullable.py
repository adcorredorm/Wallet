"""Add user_id (NULLABLE) to domain models; backfill or delete orphans.

Two-phase migration step (b):
- Drops old UNIQUE constraint on client_id in each domain table.
- Adds user_id as NULLABLE FK to users.id.
- Adds composite UNIQUE(user_id, client_id) to each domain table.
- Updates user_settings: drops old PK on key, adds user_id column,
  creates new composite PK (user_id, key).
- Backfills user_id to the first user found in users table, or deletes
  orphan rows if no users exist yet.

Revision ID: 008b_user_id_nullable
Revises: 008a_users_refresh_tokens
Create Date: 2026-03-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "008b_user_id_nullable"
down_revision: Union[str, None] = "008a_users_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that inherit from BaseModel and need user_id + composite client_id constraint.
# Maps table_name -> (old_unique_constraint_name, new_unique_constraint_name)
DOMAIN_TABLES = [
    ("accounts", "accounts_client_id_key", "uq_accounts_user_client"),
    ("categories", "categories_client_id_key", "uq_categories_user_client"),
    ("transactions", "transactions_client_id_key", "uq_transactions_user_client"),
    ("transfers", "transfers_client_id_key", "uq_transfers_user_client"),
    ("dashboards", "dashboards_client_id_key", "uq_dashboards_user_client"),
    ("dashboard_widgets", "dashboard_widgets_client_id_key", "uq_widgets_user_client"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # --- Domain tables: drop old unique(client_id), add user_id, add composite unique ---
    for table, old_constraint, new_constraint in DOMAIN_TABLES:
        # Drop the old table-level unique constraint on client_id.
        # Use IF EXISTS via raw SQL to be safe if constraint name differs.
        conn.execute(
            sa.text(
                f"ALTER TABLE {table} "
                f"DROP CONSTRAINT IF EXISTS {old_constraint}"
            )
        )
        # Also drop the unique index that may have been created separately
        conn.execute(
            sa.text(
                f"DROP INDEX IF EXISTS idx_{table}_client_id"
            )
        )

        # Add user_id NULLABLE FK
        op.add_column(
            table,
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            f"fk_{table}_user_id",
            table,
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(f"idx_{table}_user_id", table, ["user_id"])

        # Composite unique constraint: only enforced when both columns are non-null.
        # PostgreSQL unique constraints ignore rows where any column is NULL.
        op.create_unique_constraint(new_constraint, table, ["user_id", "client_id"])

    # --- user_settings: restructure to composite PK ---
    # Drop old PK (key was the sole primary key)
    op.drop_constraint("user_settings_pkey", "user_settings", type_="primary")

    # Add user_id column (nullable for now — will be filled in backfill below)
    op.add_column(
        "user_settings",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # --- Backfill: assign all rows to the first user, or delete if none ---
    result = conn.execute(
        sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    ).fetchone()

    if result is not None:
        first_user_id = result[0]
        for table, _, _ in DOMAIN_TABLES:
            conn.execute(
                sa.text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
                {"uid": first_user_id},
            )
        conn.execute(
            sa.text("UPDATE user_settings SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": first_user_id},
        )
    else:
        # No users exist: delete all orphan domain data (test / empty environment)
        for table, _, _ in DOMAIN_TABLES:
            conn.execute(sa.text(f"DELETE FROM {table} WHERE user_id IS NULL"))
        conn.execute(sa.text("DELETE FROM user_settings WHERE user_id IS NULL"))

    # Add FK constraint on user_settings.user_id now that it is populated
    op.create_foreign_key(
        "fk_user_settings_user_id",
        "user_settings",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # New composite PK for user_settings
    op.create_primary_key("pk_user_settings", "user_settings", ["user_id", "key"])


def downgrade() -> None:
    # Restore user_settings old PK
    op.drop_constraint("pk_user_settings", "user_settings", type_="primary")
    op.drop_constraint("fk_user_settings_user_id", "user_settings", type_="foreignkey")
    op.drop_column("user_settings", "user_id")
    op.create_primary_key("user_settings_pkey", "user_settings", ["key"])

    for table, old_constraint, new_constraint in reversed(DOMAIN_TABLES):
        op.drop_constraint(new_constraint, table, type_="unique")
        op.drop_index(f"idx_{table}_user_id", table_name=table)
        op.drop_constraint(f"fk_{table}_user_id", table, type_="foreignkey")
        op.drop_column(table, "user_id")
        # Restore old unique constraint on client_id
        op.create_unique_constraint(old_constraint, table, ["client_id"])
