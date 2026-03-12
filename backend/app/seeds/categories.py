"""
Seed data for predefined categories.

This module provides default categories for income and expenses based on
common personal finance categorization.
"""

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


def seed_categories() -> None:
    """
    Seed the database with predefined categories.

    Creates parent categories and their subcategories if they don't already exist.
    This function is idempotent - it can be run multiple times safely.
    """
    print("Seeding categories...")

    for cat_data in CATEGORIES:
        # Check if parent category already exists
        existing = Category.query.filter_by(
            name=cat_data["name"], parent_category_id=None
        ).first()

        if existing:
            print(f"  - Categoria '{cat_data['name']}' ya existe, omitiendo...")
            parent = existing
        else:
            # Create parent category
            parent = Category(
                name=cat_data["name"],
                type=cat_data["type"],
                icon=cat_data.get("icon"),
                color=cat_data.get("color"),
            )
            db.session.add(parent)
            db.session.flush()  # Flush to get the ID
            print(f"  + Categoria '{cat_data['name']}' creada")

        # Create subcategories if they exist
        if "subcategories" in cat_data:
            for subcat_data in cat_data["subcategories"]:
                # Check if subcategory already exists
                existing_sub = Category.query.filter_by(
                    name=subcat_data["name"], parent_category_id=parent.id
                ).first()

                if existing_sub:
                    print(
                        f"    - Subcategoria '{subcat_data['name']}' ya existe, omitiendo..."
                    )
                else:
                    # Create subcategory with same type and color as parent
                    subcategory = Category(
                        name=subcat_data["name"],
                        type=cat_data["type"],
                        icon=subcat_data.get("icon"),
                        color=cat_data.get("color"),  # Inherit parent color
                        parent_category_id=parent.id,
                    )
                    db.session.add(subcategory)
                    print(f"    + Subcategoria '{subcat_data['name']}' creada")

    # Commit all changes
    db.session.commit()
    print("Categorias seeded exitosamente!")


if __name__ == "__main__":
    # Allow running this script directly for testing
    from app import create_app

    app = create_app()
    with app.app_context():
        seed_categories()
