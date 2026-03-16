"""Rename client_id to offline_id in all domain tables

Revision ID: 009_rename_offline_id  (shortened from 009_rename_client_id_to_offline_id — alembic_version.version_num is VARCHAR(32))
Revises: 008c_user_id_not_null
Create Date: 2026-03-16

Changes:
- Column: client_id -> offline_id (6 tables)
- Unique constraints: uq_*_user_client -> uq_*_user_offline
- Indexes: create idx_*_offline_id on 5 tables
  (the old idx_*_client_id indexes were already dropped in migration 008b --
   do NOT attempt to drop them here, they no longer exist)
"""

from alembic import op

revision = "009_rename_offline_id"
down_revision = "008c_user_id_not_null"
branch_labels = None
depends_on = None

# Tables and their constraint names.
# new_index is set for tables that should have an index on offline_id.
# old_index is None for all tables because 008b already dropped idx_*_client_id.
TABLES = [
    {
        "table": "accounts",
        "old_constraint": "uq_accounts_user_client",
        "new_constraint": "uq_accounts_user_offline",
        "new_index": "idx_accounts_offline_id",
    },
    {
        "table": "categories",
        "old_constraint": "uq_categories_user_client",
        "new_constraint": "uq_categories_user_offline",
        "new_index": "idx_categories_offline_id",
    },
    {
        "table": "transactions",
        "old_constraint": "uq_transactions_user_client",
        "new_constraint": "uq_transactions_user_offline",
        "new_index": "idx_transactions_offline_id",
    },
    {
        "table": "transfers",
        "old_constraint": "uq_transfers_user_client",
        "new_constraint": "uq_transfers_user_offline",
        "new_index": "idx_transfers_offline_id",
    },
    {
        "table": "dashboards",
        "old_constraint": "uq_dashboards_user_client",
        "new_constraint": "uq_dashboards_user_offline",
        "new_index": "idx_dashboards_offline_id",
    },
    {
        "table": "dashboard_widgets",
        "old_constraint": "uq_widgets_user_client",
        "new_constraint": "uq_widgets_user_offline",
        "new_index": None,  # no index needed on this table
    },
]


def upgrade() -> None:
    """Rename client_id column to offline_id across all 6 domain tables.

    For each table:
    1. Drop old unique constraint (uq_*_user_client)
    2. Rename column client_id -> offline_id
    3. Re-create unique constraint with new name (uq_*_user_offline)
    4. Create new index idx_*_offline_id (where applicable)

    Note: idx_*_client_id indexes were already dropped in migration 008b.
    Do not attempt to drop them here.
    """
    for t in TABLES:
        table = t["table"]

        # 1. Drop old unique constraint
        op.drop_constraint(t["old_constraint"], table, type_="unique")

        # 2. Rename column
        op.alter_column(table, "client_id", new_column_name="offline_id")

        # 3. Re-create unique constraint with new name on renamed column
        op.create_unique_constraint(
            t["new_constraint"], table, ["user_id", "offline_id"]
        )

        # 4. Create new index on offline_id (old idx_*_client_id was dropped in 008b)
        if t["new_index"]:
            op.create_index(t["new_index"], table, ["offline_id"])


def downgrade() -> None:
    """Reverse the rename: offline_id -> client_id across all 6 domain tables.

    For each table (in reverse order):
    1. Drop new index idx_*_offline_id (if it was created in upgrade)
    2. Drop new unique constraint (uq_*_user_offline)
    3. Rename column offline_id -> client_id
    4. Re-create old unique constraint (uq_*_user_client)

    Note: idx_*_client_id indexes are NOT restored here — they were dropped
    in migration 008b, not in this migration. Restoring them here would
    conflict with 008b's own downgrade logic.
    """
    for t in reversed(TABLES):
        table = t["table"]

        # Drop new index (if it was created in upgrade)
        if t["new_index"]:
            op.drop_index(t["new_index"], table_name=table)

        # Drop new constraint, rename column back, re-create old constraint
        op.drop_constraint(t["new_constraint"], table, type_="unique")
        op.alter_column(table, "offline_id", new_column_name="client_id")
        op.create_unique_constraint(
            t["old_constraint"], table, ["user_id", "client_id"]
        )
        # Note: idx_*_client_id indexes are NOT restored here — they were dropped
        # in 008b, not in this migration. Restoring them here would conflict with
        # 008b's own downgrade logic.
