"""
Seed data for predefined categories.

This module provides default categories for income and expenses based on
common personal finance categorization.

The seed_categories function requires a user_id so that per-user idempotency
checks are scoped correctly: a category that already exists for one user
should not block creation for another user.
"""

from uuid import UUID

from app.models import Category, CategoryType
from app.extensions import db


# Predefined categories based on MVP specification
CATEGORIES = [
    # INCOME CATEGORIES
    {
        "name": "Salario",
        "type": CategoryType.INCOME,
        "icon": "💰",
        "color": "#10B981",
    },
    {
        "name": "Freelance",
        "type": CategoryType.INCOME,
        "icon": "💼",
        "color": "#3B82F6",
    },
    {
        "name": "Inversiones",
        "type": CategoryType.INCOME,
        "icon": "📈",
        "color": "#8B5CF6",
    },
    {
        "name": "Otros Ingresos",
        "type": CategoryType.INCOME,
        "icon": "🎁",
        "color": "#EC4899",
    },
    # EXPENSE CATEGORIES
    {
        "name": "Alimentación",
        "type": CategoryType.EXPENSE,
        "icon": "🛒",
        "color": "#EF4444",
        "subcategories": [
            {"name": "Supermercado", "icon": "🛍️"},
            {"name": "Restaurantes", "icon": "🍽️"},
            {"name": "Cafetería", "icon": "☕"},
        ],
    },
    {
        "name": "Transporte",
        "type": CategoryType.EXPENSE,
        "icon": "🚗",
        "color": "#F59E0B",
        "subcategories": [
            {"name": "Gasolina", "icon": "⛽"},
            {"name": "Transporte Público", "icon": "🚌"},
            {"name": "Taxi/Uber", "icon": "🚕"},
        ],
    },
    {
        "name": "Vivienda",
        "type": CategoryType.EXPENSE,
        "icon": "🏠",
        "color": "#6366F1",
        "subcategories": [
            {"name": "Renta", "icon": "🔑"},
            {"name": "Servicios", "icon": "⚡"},
            {"name": "Mantenimiento", "icon": "🔧"},
        ],
    },
    {
        "name": "Entretenimiento",
        "type": CategoryType.EXPENSE,
        "icon": "🎬",
        "color": "#EC4899",
        "subcategories": [
            {"name": "Streaming", "icon": "📺"},
            {"name": "Cine", "icon": "🎟️"},
            {"name": "Eventos", "icon": "📅"},
        ],
    },
    {
        "name": "Salud",
        "type": CategoryType.EXPENSE,
        "icon": "❤️",
        "color": "#14B8A6",
        "subcategories": [
            {"name": "Medicamentos", "icon": "💊"},
            {"name": "Consultas", "icon": "🩺"},
            {"name": "Gimnasio", "icon": "💪"},
        ],
    },
    {
        "name": "Educación",
        "type": CategoryType.EXPENSE,
        "icon": "📖",
        "color": "#8B5CF6",
        "subcategories": [
            {"name": "Cursos", "icon": "🎓"},
            {"name": "Libros", "icon": "📚"},
            {"name": "Material", "icon": "✏️"},
        ],
    },
    {
        "name": "Compras",
        "type": CategoryType.EXPENSE,
        "icon": "🛍️",
        "color": "#F97316",
        "subcategories": [
            {"name": "Ropa", "icon": "👕"},
            {"name": "Tecnología", "icon": "💻"},
            {"name": "Hogar", "icon": "🛋️"},
        ],
    },
    {
        "name": "Otros Gastos",
        "type": CategoryType.EXPENSE,
        "icon": "📝",
        "color": "#6B7280",
    },
]


def seed_categories(user_id: UUID) -> None:
    """
    Seed the database with predefined categories for a specific user.

    Creates parent categories and their subcategories if they don't already
    exist for this user.  This function is idempotent — it can be called
    multiple times for the same user safely.

    Args:
        user_id: The UUID of the user whose categories should be seeded.
    """
    print(f"Seeding categories for user {user_id}...")

    for cat_data in CATEGORIES:
        # Check if parent category already exists for this user
        existing = db.session.execute(
            db.select(Category).where(
                Category.user_id == user_id,
                Category.name == cat_data["name"],
                Category.parent_category_id == None,
            )
        ).scalar_one_or_none()

        if existing:
            print(f"  - Categoria '{cat_data['name']}' ya existe para este usuario, omitiendo...")
            parent = existing
        else:
            parent = Category(
                user_id=user_id,
                name=cat_data["name"],
                type=cat_data["type"],
                icon=cat_data.get("icon"),
                color=cat_data.get("color"),
            )
            db.session.add(parent)
            db.session.flush()
            print(f"  + Categoria '{cat_data['name']}' creada")

        for subcat_data in cat_data.get("subcategories", []):
            existing_sub = db.session.execute(
                db.select(Category).where(
                    Category.user_id == user_id,
                    Category.name == subcat_data["name"],
                    Category.parent_category_id == parent.id,
                )
            ).scalar_one_or_none()

            if existing_sub:
                print(f"    - Subcategoria '{subcat_data['name']}' ya existe, omitiendo...")
            else:
                subcategory = Category(
                    user_id=user_id,
                    name=subcat_data["name"],
                    type=cat_data["type"],
                    icon=subcat_data.get("icon"),
                    color=cat_data.get("color"),
                    parent_category_id=parent.id,
                )
                db.session.add(subcategory)
                print(f"    + Subcategoria '{subcat_data['name']}' creada")

    db.session.commit()
    print("Categorias seeded exitosamente!")


if __name__ == "__main__":
    # Allow running this script directly for testing.
    # Requires a user_id to be provided as an argument.
    import sys
    from uuid import UUID as _UUID

    if len(sys.argv) < 2:
        print("Usage: python -m app.seeds.categories <user_uuid>")
        sys.exit(1)

    from app import create_app

    app = create_app()
    with app.app_context():
        seed_categories(_UUID(sys.argv[1]))
