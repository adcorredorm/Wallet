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


def _seed_accounts(user_id, db) -> dict:
    """Seed test accounts. Returns {slug: Account} mapping."""
    from app.models.account import Account, AccountType

    print("Seeding accounts...")

    ACCOUNT_DEFS = [
        ("principal-cop",  "Principal COP",  AccountType.DEBIT,  "COP"),
        ("inversion-cop",  "Inversión COP",  AccountType.DEBIT,  "COP"),
        ("efectivo-cop",   "Efectivo COP",   AccountType.CASH,   "COP"),
        ("credito-cop",    "Crédito COP",    AccountType.CREDIT, "COP"),
        ("ahorro-usd",     "Ahorro USD",     AccountType.DEBIT,  "USD"),
        ("credito-usd",    "Crédito USD",    AccountType.CREDIT, "USD"),
        ("vacaciones-brl", "Vacaciones BRL", AccountType.DEBIT,  "BRL"),
    ]

    accs = {}
    for slug, name, atype, currency in ACCOUNT_DEFS:
        acc = Account(
            user_id=user_id,
            offline_id=f"test-account-{slug}",
            name=name,
            type=atype,
            currency=currency,
            active=True,
            description=None,
            tags=["test"],
        )
        db.session.add(acc)
        db.session.flush()
        accs[slug] = acc

    print(f"  Created {len(accs)} accounts")
    return accs


def _seed_categories(user_id, db) -> dict:
    """Seed test categories. Returns {slug: Category} mapping."""
    from app.models.category import Category, CategoryType

    print("Seeding categories...")

    CATEGORY_DEFS = [
        # income
        ("salario",           "Salario Test",            CategoryType.INCOME,   []),
        ("rendimientos",      "Rendimientos Test",        CategoryType.INCOME,   []),
        ("interes-inversion", "Interés Inversión Test",  CategoryType.INCOME,   []),
        # expense
        ("facturas",      "Facturas Test",      CategoryType.EXPENSE, [
            ("facturas-arriendo",   "Arriendo"),
            ("facturas-servicios",  "Servicios"),
            ("facturas-internet",   "Internet"),
        ]),
        ("comida",        "Comida Test",        CategoryType.EXPENSE, [
            ("comida-mercado",      "Mercado"),
            ("comida-extra",        "Extra"),
            ("comida-restaurantes", "Restaurantes"),
            ("comida-antojos",      "Antojos"),
        ]),
        ("salidas",       "Salidas Test",       CategoryType.EXPENSE, [
            ("salidas-bares",   "Bares"),
            ("salidas-eventos", "Eventos"),
        ]),
        ("compras",       "Compras Test",       CategoryType.EXPENSE, [
            ("compras-ropa",       "Ropa"),
            ("compras-tecnologia", "Tecnología"),
        ]),
        ("transporte",    "Transporte Test",    CategoryType.EXPENSE, []),
        ("regalos",       "Regalos Test",       CategoryType.EXPENSE, []),
        ("viaje-brasil",  "Viaje Brasil Test",  CategoryType.EXPENSE, [
            ("viaje-brasil-hospedaje",   "Hospedaje"),
            ("viaje-brasil-comida",      "Comida BRL"),
            ("viaje-brasil-actividades", "Actividades"),
        ]),
    ]

    cats = {}
    for slug, name, ctype, subcats in CATEGORY_DEFS:
        parent = Category(
            user_id=user_id,
            offline_id=f"test-category-{slug}",
            name=name,
            type=ctype,
            active=True,
        )
        db.session.add(parent)
        db.session.flush()
        cats[slug] = parent

        for sub_slug, sub_name in subcats:
            child = Category(
                user_id=user_id,
                offline_id=f"test-category-{sub_slug}",
                name=sub_name,
                type=ctype,
                active=True,
                parent_category_id=parent.id,
            )
            db.session.add(child)
            db.session.flush()
            cats[sub_slug] = child

    print(f"  Created {len(cats)} categories")
    return cats


def _clean_test_data(user_id, db) -> None:
    from app.models.dashboard_widget import DashboardWidget
    from app.models.dashboard import Dashboard
    from app.models.transaction import Transaction
    from app.models.transfer import Transfer
    from app.models.account import Account
    from app.models.category import Category

    print("Cleaning previous test data...")

    for Model in [DashboardWidget, Dashboard, Transaction, Transfer, Account]:
        deleted = db.session.execute(
            db.delete(Model).where(
                Model.user_id == user_id,
                Model.offline_id.like("test-%"),
            )
        ).rowcount
        print(f"  Deleted {deleted} {Model.__tablename__}")

    # Handle Category deletion in two steps to respect the self-referential FK
    # First delete subcategories (where parent_category_id IS NOT NULL)
    deleted_subs = db.session.execute(
        db.delete(Category).where(
            Category.user_id == user_id,
            Category.offline_id.like("test-%"),
            Category.parent_category_id.isnot(None),
        )
    ).rowcount
    print(f"  Deleted {deleted_subs} test subcategories")

    # Then delete parent categories (where parent_category_id IS NULL)
    deleted_parents = db.session.execute(
        db.delete(Category).where(
            Category.user_id == user_id,
            Category.offline_id.like("test-%"),
            Category.parent_category_id.is_(None),
        )
    ).rowcount
    print(f"  Deleted {deleted_parents} test parent categories")

    db.session.commit()
    print("Clean done.")


# ---------------------------------------------------------------------------
# Transaction helpers
# ---------------------------------------------------------------------------

def _make_tx(user_id, account, category, tx_type, amount, tx_date,
             offline_id, original_amount=None, original_currency=None,
             exchange_rate=None, base_rate=None):
    from app.models.transaction import Transaction, TransactionType
    return Transaction(
        user_id=user_id,
        offline_id=offline_id,
        account_id=account.id,
        category_id=category.id,
        type=TransactionType.INCOME if tx_type == "income" else TransactionType.EXPENSE,
        amount=amount,
        date=tx_date,
        original_amount=original_amount,
        original_currency=original_currency,
        exchange_rate=exchange_rate,
        base_rate=base_rate or BASE_RATES.get(account.currency, 1.0),
    )


def _seed_credito_cop_expenses(user_id, accs, cats, months, db) -> dict:
    """
    Seed Crédito COP expense transactions (~20-30/month).
    Returns {(year, month): total_cop_expenses}.
    """
    print("Seeding Crédito COP expenses...")

    acc = accs["credito-cop"]

    # (category_slug, freq_min, freq_max, amount_min, amount_max)
    EXPENSE_TYPES = [
        ("comida-restaurantes", 6, 8,  25_000,  80_000),
        ("comida-antojos",      3, 5,   8_000,  25_000),
        ("salidas-bares",       2, 3,  40_000, 120_000),
        ("salidas-eventos",     1, 2,  50_000, 200_000),
        ("compras-ropa",        1, 2,  80_000, 300_000),
        ("compras-tecnologia",  0, 1, 100_000, 500_000),
        ("transporte",          4, 6,  10_000,  35_000),
        ("regalos",             1, 2,  30_000, 150_000),
    ]

    monthly_totals = {}
    total_tx = 0

    for year, month in months:
        month_total = 0
        seq = 0
        last = month_last_day(year, month)
        # Use Mon-Sat days (weekday 0-5), with occasional Sunday
        available_days = [
            date(year, month, d)
            for d in range(1, last + 1)
            if date(year, month, d).weekday() < 6
        ]
        random.shuffle(available_days)
        day_idx = 0

        for cat_slug, freq_min, freq_max, amt_min, amt_max in EXPENSE_TYPES:
            count = random.randint(freq_min, freq_max)
            for _ in range(count):
                amount = random.randint(amt_min, amt_max)
                tx_date = available_days[day_idx % len(available_days)]
                day_idx += 1
                seq += 1
                offline_id = f"test-tx-credito-cop-{year:04d}-{month:02d}-{seq:02d}"
                tx = _make_tx(user_id, acc, cats[cat_slug], "expense", amount, tx_date, offline_id)
                db.session.add(tx)
                month_total += amount
                total_tx += 1

        monthly_totals[(year, month)] = month_total

    print(f"  Created {total_tx} Crédito COP expense transactions")
    return monthly_totals


def _seed_credito_usd_expenses(user_id, accs, cats, months, db) -> dict:
    """
    Seed Crédito USD expense transactions (0-2/month, 60% chance any month has tx).
    Returns {(year, month): total_usd_expenses}.
    """
    print("Seeding Crédito USD expenses...")

    acc = accs["credito-usd"]
    monthly_totals = {}
    total_tx = 0

    CAT_CHOICES = ["compras-tecnologia", "salidas-eventos"]

    for year, month in months:
        month_total = 0.0
        seq = 0
        if random.random() < 0.60:
            count = random.randint(1, 2)
            for _ in range(count):
                amount_usd = round(random.uniform(50, 400), 2)
                tx_date = rand_day(year, month)
                seq += 1
                offline_id = f"test-tx-credito-usd-{year:04d}-{month:02d}-{seq:02d}"
                cat_slug = random.choice(CAT_CHOICES)
                tx = _make_tx(user_id, acc, cats[cat_slug], "expense", amount_usd, tx_date, offline_id)
                db.session.add(tx)
                month_total += amount_usd
                total_tx += 1
        monthly_totals[(year, month)] = month_total

    print(f"  Created {total_tx} Crédito USD expense transactions")
    return monthly_totals


def _seed_principal_bills(user_id, accs, cats, months, db) -> None:
    """Seed Principal COP fixed monthly bill expenses (4 transactions/month)."""
    print("Seeding Principal COP bills...")

    acc = accs["principal-cop"]
    # The extra bill randomly picks from these subcategories
    EXTRA_SUBS = ["facturas-arriendo", "facturas-servicios", "facturas-internet"]
    total_tx = 0

    for year, month in months:
        seq = 0
        last = month_last_day(year, month)

        # Fixed bills on fixed days
        for cat_slug, amount, fixed_day in [
            ("facturas-arriendo",  1_200_000, 1),
            ("facturas-servicios",   180_000, 5),
            ("facturas-internet",     85_000, 8),
        ]:
            tx_date = date(year, month, min(fixed_day, last))
            seq += 1
            offline_id = f"test-tx-principal-cop-bills-{year:04d}-{month:02d}-{seq:02d}"
            db.session.add(_make_tx(user_id, acc, cats[cat_slug], "expense", amount, tx_date, offline_id))
            total_tx += 1

        # One extra variable bill
        extra_slug = random.choice(EXTRA_SUBS)
        extra_amount = random.randint(60_000, 150_000)
        extra_date = rand_day(year, month, 3, 15)
        seq += 1
        offline_id = f"test-tx-principal-cop-bills-{year:04d}-{month:02d}-{seq:02d}"
        db.session.add(_make_tx(user_id, acc, cats[extra_slug], "expense", extra_amount, extra_date, offline_id))
        total_tx += 1

    print(f"  Created {total_tx} Principal COP bill transactions")


def _seed_vacaciones_brl_expenses(user_id, accs, cats, vac_month, db) -> None:
    """Seed Vacaciones BRL expenses — only active during the vacation month."""
    print("Seeding Vacaciones BRL expenses...")

    acc = accs["vacaciones-brl"]
    year, month = vac_month
    last = month_last_day(year, month)

    EXPENSE_PLAN = [
        ("viaje-brasil-hospedaje",   3, 300, 600),
        ("viaje-brasil-comida",      8,  40, 150),
        ("viaje-brasil-actividades", 7,  80, 350),
    ]

    all_days = list(range(1, last + 1))
    random.shuffle(all_days)
    day_cursor = 0
    seq = 0
    total_tx = 0

    for cat_slug, count, amt_min, amt_max in EXPENSE_PLAN:
        for _ in range(count):
            amount = round(random.uniform(amt_min, amt_max), 2)
            tx_date = date(year, month, all_days[day_cursor % len(all_days)])
            day_cursor += 1
            seq += 1
            offline_id = f"test-tx-vacaciones-brl-{year:04d}-{month:02d}-{seq:02d}"
            tx = _make_tx(
                user_id, acc, cats[cat_slug], "expense", amount, tx_date, offline_id,
                base_rate=BASE_RATES["BRL"]
            )
            db.session.add(tx)
            total_tx += 1

    print(f"  Created {total_tx} Vacaciones BRL expense transactions")


def _seed_income_transactions(user_id, accs, cats, months, db) -> None:
    """Seed income: monthly salary (cross-currency USD→COP), bimonthly returns, quarterly interest."""
    print("Seeding income transactions...")

    principal = accs["principal-cop"]
    inversion = accs["inversion-cop"]
    total_tx = 0

    for i, (year, month) in enumerate(months):
        # --- Salary (cross-currency USD→COP, monthly) ---
        rate = sample_rate(USD_TO_COP_BASE)           # COP per 1 USD, ±20% variation
        original_usd = round(random.uniform(2_850, 3_150), 2)
        amount_cop = round(original_usd * rate, 2)
        salary_day = rand_day(year, month, 3, 7)
        offline_id = f"test-tx-principal-cop-salary-{year:04d}-{month:02d}-01"
        db.session.add(_make_tx(
            user_id, principal, cats["salario"], "income", amount_cop, salary_day, offline_id,
            original_amount=original_usd,
            original_currency="USD",
            exchange_rate=rate,
            base_rate=BASE_RATES["COP"],
        ))
        total_tx += 1

        # --- Investment returns (every 2 months: indices 1, 3, 5, 7, 9, 11, 13) ---
        if i % 2 == 1:
            amount = random.randint(300_000, 800_000)
            rend_day = rand_day(year, month)
            offline_id = f"test-tx-principal-cop-rend-{year:04d}-{month:02d}-01"
            db.session.add(_make_tx(
                user_id, principal, cats["rendimientos"], "income", amount, rend_day, offline_id
            ))
            total_tx += 1

        # --- Quarterly interest on Inversión COP (indices 2, 5, 8, 11, 14) ---
        if i % 3 == 2:
            amount = random.randint(150_000, 400_000)
            int_day = rand_day(year, month, 10, 20)
            offline_id = f"test-tx-inversion-cop-interes-{year:04d}-{month:02d}-01"
            db.session.add(_make_tx(
                user_id, inversion, cats["interes-inversion"], "income", amount, int_day, offline_id
            ))
            total_tx += 1

    print(f"  Created {total_tx} income transactions")


def _seed_efectivo_spending(user_id, accs, cats, months, db) -> list:
    """
    Seed Efectivo COP spending with sawtooth balance pattern.
    Guarantees 5-8 transactions per week using random.sample.
    Returns list of (date, 200_000) replenishment transfers needed.
    """
    print("Seeding Efectivo COP spending...")

    from datetime import timedelta

    acc = accs["efectivo-cop"]
    COMIDA_SUBS = ["comida-mercado", "comida-antojos"]

    refills = []
    balance = 0.0
    seq_global = 0

    if not months:
        return refills

    start_date = date(months[0][0], months[0][1], 1)
    end_date = date.today()

    # Initial refill on day 1
    refills.append((start_date, 200_000))
    balance = 200_000.0

    current = start_date
    while current <= end_date:
        # Collect available days in this week
        week_days = []
        for day_offset in range(7):
            d = current + timedelta(days=day_offset)
            if d <= end_date:
                week_days.append(d)
        if not week_days:
            current += timedelta(days=7)
            continue

        # Guarantee 5-8 transactions this week
        week_txs = random.randint(5, 8)
        chosen_days = sorted(random.sample(week_days, min(week_txs, len(week_days))))

        for tx_date in chosen_days:
            amount = random.randint(5_000, 35_000)
            # Refill if balance would drop below 20,000
            if balance - amount < 20_000:
                refills.append((tx_date, 200_000))
                balance += 200_000.0

            cat_slug = random.choice(COMIDA_SUBS) if random.random() < 0.6 else "transporte"
            seq_global += 1
            offline_id = f"test-tx-efectivo-cop-{tx_date.year:04d}-{tx_date.month:02d}-{seq_global:03d}"
            db.session.add(_make_tx(
                user_id, acc, cats[cat_slug], "expense", amount, tx_date, offline_id
            ))
            balance -= amount

        current += timedelta(days=7)

    print(f"  Created {seq_global} Efectivo COP spending transactions, {len(refills)} refills needed")
    return refills


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
