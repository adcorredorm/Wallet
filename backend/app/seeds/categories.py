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
        "nombre": "Salario",
        "tipo": CategoryType.INGRESO,
        "icono": "💰",
        "color": "#10B981",
    },
    {
        "nombre": "Freelance",
        "tipo": CategoryType.INGRESO,
        "icono": "💼",
        "color": "#3B82F6",
    },
    {
        "nombre": "Inversiones",
        "tipo": CategoryType.INGRESO,
        "icono": "📈",
        "color": "#8B5CF6",
    },
    {
        "nombre": "Otros Ingresos",
        "tipo": CategoryType.INGRESO,
        "icono": "🎁",
        "color": "#EC4899",
    },
    # EXPENSE CATEGORIES
    {
        "nombre": "Alimentación",
        "tipo": CategoryType.GASTO,
        "icono": "🛒",
        "color": "#EF4444",
        "subcategorias": [
            {"nombre": "Supermercado", "icono": "🛍️"},
            {"nombre": "Restaurantes", "icono": "🍽️"},
            {"nombre": "Cafetería", "icono": "☕"},
        ],
    },
    {
        "nombre": "Transporte",
        "tipo": CategoryType.GASTO,
        "icono": "🚗",
        "color": "#F59E0B",
        "subcategorias": [
            {"nombre": "Gasolina", "icono": "⛽"},
            {"nombre": "Transporte Público", "icono": "🚌"},
            {"nombre": "Taxi/Uber", "icono": "🚕"},
        ],
    },
    {
        "nombre": "Vivienda",
        "tipo": CategoryType.GASTO,
        "icono": "🏠",
        "color": "#6366F1",
        "subcategorias": [
            {"nombre": "Renta", "icono": "🔑"},
            {"nombre": "Servicios", "icono": "⚡"},
            {"nombre": "Mantenimiento", "icono": "🔧"},
        ],
    },
    {
        "nombre": "Entretenimiento",
        "tipo": CategoryType.GASTO,
        "icono": "🎬",
        "color": "#EC4899",
        "subcategorias": [
            {"nombre": "Streaming", "icono": "📺"},
            {"nombre": "Cine", "icono": "🎟️"},
            {"nombre": "Eventos", "icono": "📅"},
        ],
    },
    {
        "nombre": "Salud",
        "tipo": CategoryType.GASTO,
        "icono": "❤️",
        "color": "#14B8A6",
        "subcategorias": [
            {"nombre": "Medicamentos", "icono": "💊"},
            {"nombre": "Consultas", "icono": "🩺"},
            {"nombre": "Gimnasio", "icono": "💪"},
        ],
    },
    {
        "nombre": "Educación",
        "tipo": CategoryType.GASTO,
        "icono": "📖",
        "color": "#8B5CF6",
        "subcategorias": [
            {"nombre": "Cursos", "icono": "🎓"},
            {"nombre": "Libros", "icono": "📚"},
            {"nombre": "Material", "icono": "✏️"},
        ],
    },
    {
        "nombre": "Compras",
        "tipo": CategoryType.GASTO,
        "icono": "🛍️",
        "color": "#F97316",
        "subcategorias": [
            {"nombre": "Ropa", "icono": "👕"},
            {"nombre": "Tecnología", "icono": "💻"},
            {"nombre": "Hogar", "icono": "🛋️"},
        ],
    },
    {
        "nombre": "Otros Gastos",
        "tipo": CategoryType.GASTO,
        "icono": "📝",
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
            nombre=cat_data["nombre"], categoria_padre_id=None
        ).first()

        if existing:
            print(f"  - Categoria '{cat_data['nombre']}' ya existe, omitiendo...")
            parent = existing
        else:
            # Create parent category
            parent = Category(
                nombre=cat_data["nombre"],
                tipo=cat_data["tipo"],
                icono=cat_data.get("icono"),
                color=cat_data.get("color"),
            )
            db.session.add(parent)
            db.session.flush()  # Flush to get the ID
            print(f"  + Categoria '{cat_data['nombre']}' creada")

        # Create subcategories if they exist
        if "subcategorias" in cat_data:
            for subcat_data in cat_data["subcategorias"]:
                # Check if subcategory already exists
                existing_sub = Category.query.filter_by(
                    nombre=subcat_data["nombre"], categoria_padre_id=parent.id
                ).first()

                if existing_sub:
                    print(
                        f"    - Subcategoria '{subcat_data['nombre']}' ya existe, omitiendo..."
                    )
                else:
                    # Create subcategory with same type and color as parent
                    subcategory = Category(
                        nombre=subcat_data["nombre"],
                        tipo=cat_data["tipo"],
                        icono=subcat_data.get("icono"),
                        color=cat_data.get("color"),  # Inherit parent color
                        categoria_padre_id=parent.id,
                    )
                    db.session.add(subcategory)
                    print(f"    + Subcategoria '{subcat_data['nombre']}' creada")

    # Commit all changes
    db.session.commit()
    print("Categorias seeded exitosamente!")


if __name__ == "__main__":
    # Allow running this script directly for testing
    from app import create_app

    app = create_app()
    with app.app_context():
        seed_categories()
