"""add_recurring_rules

Revision ID: 2c7f9c3fdbaa
Revises: 9135c3a6f6c0
Create Date: 2026-03-29 10:07:01.554841

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2c7f9c3fdbaa'
down_revision = '9135c3a6f6c0'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Create new enum types only if they don't exist yet
    bind.execute(sa.text(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recurringfrequency') THEN "
        "    CREATE TYPE recurringfrequency AS ENUM ('DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'); "
        "  END IF; "
        "END $$"
    ))
    bind.execute(sa.text(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recurringrulestatus') THEN "
        "    CREATE TYPE recurringrulestatus AS ENUM ('ACTIVE', 'PAUSED', 'COMPLETED'); "
        "  END IF; "
        "END $$"
    ))

    # Create recurring_rules table using raw SQL to avoid Alembic re-emitting
    # existing enum types (transactiontype is already in DB from previous migrations)
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS recurring_rules (
            id UUID NOT NULL,
            offline_id VARCHAR(100),
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            user_id UUID,
            title VARCHAR(100) NOT NULL,
            type transactiontype NOT NULL,
            amount NUMERIC(20, 8) NOT NULL,
            account_id UUID NOT NULL,
            category_id UUID NOT NULL,
            description VARCHAR(500),
            tags VARCHAR(50)[] NOT NULL,
            requires_confirmation BOOLEAN NOT NULL,
            frequency recurringfrequency NOT NULL,
            interval INTEGER NOT NULL,
            day_of_month INTEGER,
            start_date DATE NOT NULL,
            end_date DATE,
            max_occurrences INTEGER,
            occurrences_created INTEGER NOT NULL,
            next_occurrence_date DATE NOT NULL,
            status recurringrulestatus NOT NULL,
            CONSTRAINT pk_recurring_rules PRIMARY KEY (id),
            CONSTRAINT uq_recurring_rules_user_offline UNIQUE (user_id, offline_id),
            CONSTRAINT fk_recurring_rules_account_id FOREIGN KEY (account_id) REFERENCES accounts(id),
            CONSTRAINT fk_recurring_rules_category_id FOREIGN KEY (category_id) REFERENCES categories(id),
            CONSTRAINT fk_recurring_rules_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """))

    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_recurring_rules_account ON recurring_rules (account_id)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_recurring_rules_category ON recurring_rules (category_id)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_recurring_rules_user_status ON recurring_rules (user_id, status)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_recurring_rules_offline_id ON recurring_rules (offline_id)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_recurring_rules_user_id ON recurring_rules (user_id)"))

    # Add recurring_rule_id FK to transactions
    bind.execute(sa.text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS recurring_rule_id UUID"))
    bind.execute(sa.text(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_transactions_recurring_rule_id') THEN "
        "    ALTER TABLE transactions ADD CONSTRAINT fk_transactions_recurring_rule_id "
        "    FOREIGN KEY (recurring_rule_id) REFERENCES recurring_rules(id); "
        "  END IF; "
        "END $$"
    ))


def downgrade():
    bind = op.get_bind()

    bind.execute(sa.text(
        "DO $$ BEGIN "
        "  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_transactions_recurring_rule_id') THEN "
        "    ALTER TABLE transactions DROP CONSTRAINT fk_transactions_recurring_rule_id; "
        "  END IF; "
        "END $$"
    ))
    bind.execute(sa.text("ALTER TABLE transactions DROP COLUMN IF EXISTS recurring_rule_id"))

    bind.execute(sa.text("DROP INDEX IF EXISTS ix_recurring_rules_user_id"))
    bind.execute(sa.text("DROP INDEX IF EXISTS ix_recurring_rules_offline_id"))
    bind.execute(sa.text("DROP INDEX IF EXISTS idx_recurring_rules_user_status"))
    bind.execute(sa.text("DROP INDEX IF EXISTS idx_recurring_rules_category"))
    bind.execute(sa.text("DROP INDEX IF EXISTS idx_recurring_rules_account"))
    bind.execute(sa.text("DROP TABLE IF EXISTS recurring_rules"))
    bind.execute(sa.text("DROP TYPE IF EXISTS recurringrulestatus"))
    bind.execute(sa.text("DROP TYPE IF EXISTS recurringfrequency"))
