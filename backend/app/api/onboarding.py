"""
Onboarding API endpoint.

POST /api/v1/onboarding/seed creates predefined accounts and categories for
a newly authenticated user.  The endpoint is idempotent-guarded: if the user
already has at least one account, it returns 409 and takes no further action.
"""

from flask import Blueprint, g

from app.extensions import db
from app.models.account import Account, AccountType
from app.models.category import Category, CategoryType
from app.models.dashboard import Dashboard
from app.models.dashboard_widget import DashboardWidget, WidgetType
from app.repositories.account import AccountRepository
from app.utils.auth import require_auth
from app.utils.responses import error_response, success_response

onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/api/v1/onboarding")

_account_repo = AccountRepository()

# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

_SEED_ACCOUNTS = [
    {"name": "Efectivo", "type": AccountType.CASH, "currency": "COP"},
    {"name": "Cuenta Bancaria", "type": AccountType.DEBIT, "currency": "COP"},
    {"name": "Tarjeta de Crédito", "type": AccountType.CREDIT, "currency": "COP"},
]

_SEED_CATEGORIES = [
    # ------------------------------------------------------------------ INCOME
    {"name": "Salario", "type": CategoryType.INCOME, "icon": "💰", "color": "#10B981"},
    {"name": "Otros Ingresos", "type": CategoryType.INCOME, "icon": "🪙", "color": "#3B82F6"},
    # ----------------------------------------------------------------- EXPENSE
    {
        "name": "Alimentación",
        "type": CategoryType.EXPENSE,
        "icon": "🍽️",
        "color": "#EF4444",
        "subcategories": [
            {"name": "Mercado", "icon": "🛒"},
            {"name": "Restaurantes", "icon": "🍴"},
            {"name": "Domicilios", "icon": "🛵"},
        ],
    },
    {
        "name": "Vivienda",
        "type": CategoryType.EXPENSE,
        "icon": "🏠",
        "color": "#6366F1",
        "subcategories": [
            {"name": "Renta/Hipoteca", "icon": "🔑"},
            {"name": "Servicios", "icon": "⚡"},
            {"name": "Mantenimiento", "icon": "🔧"},
        ],
    },
    {
        "name": "Salud",
        "type": CategoryType.EXPENSE,
        "icon": "❤️",
        "color": "#14B8A6",
    },
    {
        "name": "Transporte",
        "type": CategoryType.EXPENSE,
        "icon": "🚗",
        "color": "#F59E0B",
        "subcategories": [
            {"name": "Gasolina", "icon": "⛽"},
            {"name": "Transporte Público", "icon": "🚌"},
            {"name": "Uber/Taxi", "icon": "🚕"},
        ],
    },
    {
        "name": "Facturas",
        "type": CategoryType.EXPENSE,
        "icon": "🧾",
        "color": "#8B5CF6",
    },
    {
        "name": "Entretenimiento",
        "type": CategoryType.EXPENSE,
        "icon": "🎬",
        "color": "#EC4899",
        "subcategories": [
            {"name": "Streaming", "icon": "📺"},
        ],
    },
    {
        "name": "Educación",
        "type": CategoryType.EXPENSE,
        "icon": "🎓",
        "color": "#3B82F6",
    },
    {
        "name": "Mascotas",
        "type": CategoryType.EXPENSE,
        "icon": "🐾",
        "color": "#F97316",
    },
    {
        "name": "Compras",
        "type": CategoryType.EXPENSE,
        "icon": "🛍️",
        "color": "#0EA5E9",
    },
    {
        "name": "Otros",
        "type": CategoryType.EXPENSE,
        "icon": "📦",
        "color": "#6B7280",
    },
]


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@onboarding_bp.route("/seed", methods=["POST"])
@require_auth
def seed_user():
    """
    Create predefined accounts and categories for the authenticated user.

    Idempotency guard: if the user already has at least one account the
    endpoint returns 409 without making any changes.

    Returns:
        201: Seed data created. Body contains accounts_created,
             categories_created, and dashboard_created counts.
        401: Authentication required.
        409: User already has accounts — seed was already applied.
        500: Internal server error.
    """
    user_id = g.current_user_id

    # Idempotency guard — only accounts are checked
    existing_count = _account_repo.count(user_id)
    if existing_count > 0:
        return error_response(
            "El usuario ya tiene cuentas. El seed ya fue aplicado.",
            status_code=409,
        )

    accounts_created = 0
    categories_created = 0
    dashboard_created = False

    try:
        # --- Create accounts ---
        for acc_def in _SEED_ACCOUNTS:
            offline_id = f"seed-{acc_def['name'].lower().replace(' ', '-')}"
            account = Account(
                user_id=user_id,
                name=acc_def["name"],
                type=acc_def["type"],
                currency=acc_def["currency"],
                tags=["auto-generated"],
                offline_id=offline_id,
            )
            db.session.add(account)
            accounts_created += 1

        db.session.flush()

        # --- Create categories (with subcategories) ---
        for cat_def in _SEED_CATEGORIES:
            parent_offline_id = f"seed-{cat_def['name'].lower().replace(' ', '-')}"
            parent = Category(
                user_id=user_id,
                name=cat_def["name"],
                type=cat_def["type"],
                icon=cat_def.get("icon"),
                color=cat_def.get("color"),
                offline_id=parent_offline_id,
            )
            db.session.add(parent)
            db.session.flush()  # get parent.id for subcategory FK
            categories_created += 1

            for sub_def in cat_def.get("subcategories", []):
                sub_offline_id = (
                    f"seed-{cat_def['name'].lower().replace(' ', '-')}"
                    f"-{sub_def['name'].lower().replace(' ', '-')}"
                )
                subcategory = Category(
                    user_id=user_id,
                    name=sub_def["name"],
                    type=cat_def["type"],
                    icon=sub_def.get("icon"),
                    color=cat_def.get("color"),
                    parent_category_id=parent.id,
                    offline_id=sub_offline_id,
                )
                db.session.add(subcategory)
                categories_created += 1

        # --- Create default dashboard (3 columns) ---
        dashboard = Dashboard(
            user_id=user_id,
            name="Seguimiento Mes",
            is_default=True,
            sort_order=0,
            display_currency="COP",
            layout_columns=3,
            offline_id="seed-default-dashboard",
        )
        db.session.add(dashboard)
        db.session.flush()  # get dashboard.id for widget FKs

        _time_last_30 = {"type": "dynamic", "value": "last_30_days"}
        _filters_expense = {"type": "expense"}

        # Widget 1: Gastos del Mes — número (1 col)
        db.session.add(DashboardWidget(
            user_id=user_id,
            dashboard_id=dashboard.id,
            widget_type=WidgetType.NUMBER,
            title="Gastos del Mes",
            position_x=0, position_y=0, width=1, height=1,
            config={
                "time_range": _time_last_30,
                "filters": _filters_expense,
                "granularity": "month",
                "group_by": "none",
                "aggregation": "sum",
            },
            offline_id="seed-widget-expenses-number",
        ))

        # Widget 2: Línea de Tiempo — línea mixta (2 cols) — group_by type, no filter
        db.session.add(DashboardWidget(
            user_id=user_id,
            dashboard_id=dashboard.id,
            widget_type=WidgetType.LINE,
            title="Línea de Tiempo",
            position_x=1, position_y=0, width=2, height=1,
            config={
                "time_range": _time_last_30,
                "filters": {},
                "granularity": "day",
                "group_by": "type",
                "aggregation": "sum",
            },
            offline_id="seed-widget-timeline",
        ))

        # Widget 3: Gastos por Categoría — pastel (2 cols)
        db.session.add(DashboardWidget(
            user_id=user_id,
            dashboard_id=dashboard.id,
            widget_type=WidgetType.PIE,
            title="Gastos por Categoría",
            position_x=0, position_y=1, width=2, height=2,
            config={
                "time_range": _time_last_30,
                "filters": _filters_expense,
                "granularity": "month",
                "group_by": "category",
                "aggregation": "sum",
            },
            offline_id="seed-widget-expenses-by-category",
        ))

        # Widget 4: Gastos en la Semana — barras (1 col)
        db.session.add(DashboardWidget(
            user_id=user_id,
            dashboard_id=dashboard.id,
            widget_type=WidgetType.BAR,
            title="Gastos en la Semana",
            position_x=2, position_y=1, width=1, height=1,
            config={
                "time_range": _time_last_30,
                "filters": _filters_expense,
                "granularity": "day",
                "group_by": "day_of_week",
                "aggregation": "sum",
            },
            offline_id="seed-widget-expenses-by-dow",
        ))

        dashboard_created = True

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return error_response(
            f"Error al crear datos iniciales: {str(e)}", status_code=500
        )

    return success_response(
        data={
            "accounts_created": accounts_created,
            "categories_created": categories_created,
            "dashboard_created": dashboard_created,
        },
        message="Datos iniciales creados exitosamente",
        status_code=201,
    )
