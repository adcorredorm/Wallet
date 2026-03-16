"""
WARNING: DEV/TEST ONLY — do not run in production.

This script injects realistic fake financial data into a real user account
for development and manual testing purposes. It deletes ALL data with
offline_id prefixed 'test-' for the target user before re-seeding.

Usage:
    cd backend
    python dev_seed_test_data.py --email user@example.com
"""

import argparse
import calendar
import random
from datetime import date
from dateutil.relativedelta import relativedelta

random.seed(42)

# ---------------------------------------------------------------------------
# Exchange rate constants
# ---------------------------------------------------------------------------
USD_TO_COP_BASE = 4100.0   # 1 USD ≈ 4 100 COP
BRL_TO_COP_BASE = 850.0    # 1 BRL ≈ 850 COP

BASE_RATES = {
    "COP": 1.0,
    "USD": 4100.0,
    "BRL": 850.0,
}


def sample_rate(base: float) -> float:
    """Return base rate with ±20% random variation."""
    return round(base * random.uniform(0.80, 1.20), 6)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def build_months(today: date) -> list[tuple[int, int]]:
    """Return list of (year, month) tuples for the 15-month window ending today."""
    start = today - relativedelta(months=14)
    start = start.replace(day=1)
    months = []
    cursor = start
    while cursor <= today:
        months.append((cursor.year, cursor.month))
        cursor += relativedelta(months=1)
    return months


def vacation_month(today: date) -> tuple[int, int]:
    """Return (year, month) of the vacation month (8 months before current month)."""
    d = today - relativedelta(months=8)
    return (d.year, d.month)


def month_last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def rand_day(year: int, month: int, day_min: int = 1, day_max: int = None) -> date:
    last = month_last_day(year, month)
    day_max = day_max or last
    day_max = min(day_max, last)
    return date(year, month, random.randint(day_min, day_max))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(email: str) -> None:
    from app import create_app
    from app.extensions import db

    app = create_app()
    with app.app_context():
        from app.models.user import User

        user = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar_one_or_none()

        if user is None:
            print(f"ERROR: No user found with email '{email}'")
            raise SystemExit(1)

        print(f"Seeding test data for user: {user.email} ({user.id})")
        today = date.today()
        months = build_months(today)
        vac_month = vacation_month(today)
        print(f"  Window: {months[0]} → {months[-1]}  |  Vacation month: {vac_month}")

        _clean_test_data(user.id, db)

        cats = _seed_categories(user.id, db)
        accs = _seed_accounts(user.id, db)
        monthly_credito_cop = _seed_credito_cop_expenses(user.id, accs, cats, months, db)
        monthly_credito_usd = _seed_credito_usd_expenses(user.id, accs, cats, months, db)
        _seed_principal_bills(user.id, accs, cats, months, db)
        _seed_vacaciones_brl_expenses(user.id, accs, cats, vac_month, db)
        _seed_income_transactions(user.id, accs, cats, months, db)
        efectivo_refills = _seed_efectivo_spending(user.id, accs, cats, months, db)
        _seed_credit_payment_transfers(user.id, accs, monthly_credito_cop, monthly_credito_usd, months, db)
        _seed_other_transfers(user.id, accs, months, vac_month, efectivo_refills, db)
        _seed_dashboards(user.id, accs, vac_month, db)

        db.session.commit()
        print("Done! Test data seeded successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed test data for a dev user.")
    parser.add_argument("--email", required=True, help="Email of the target user")
    args = parser.parse_args()
    main(args.email)
