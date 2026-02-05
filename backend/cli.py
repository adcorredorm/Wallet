"""
CLI commands for common development tasks.

Usage:
    python cli.py --help
"""

import click
import os
from dotenv import load_dotenv

load_dotenv()


@click.group()
def cli():
    """Wallet Backend CLI - Common development tasks."""
    pass


@cli.command()
def init_db():
    """Initialize database with schema and seed data."""
    click.echo("Initializing database...")

    # Run migrations
    click.echo("Running migrations...")
    os.system("alembic upgrade head")

    # Seed categories
    click.echo("Seeding categories...")
    from app import create_app
    from app.seeds import seed_categories

    app = create_app()
    with app.app_context():
        seed_categories()

    click.echo("Database initialized successfully!")


@cli.command()
def seed():
    """Seed database with predefined categories."""
    click.echo("Seeding database...")

    from app import create_app
    from app.seeds import seed_categories

    app = create_app()
    with app.app_context():
        seed_categories()

    click.echo("Database seeded successfully!")


@cli.command()
def reset_db():
    """Reset database (WARNING: Deletes all data)."""
    if not click.confirm("This will delete all data. Are you sure?"):
        click.echo("Aborted.")
        return

    click.echo("Resetting database...")

    # Downgrade all migrations
    click.echo("Dropping all tables...")
    os.system("alembic downgrade base")

    # Re-run migrations
    click.echo("Recreating schema...")
    os.system("alembic upgrade head")

    # Seed categories
    click.echo("Seeding categories...")
    from app import create_app
    from app.seeds import seed_categories

    app = create_app()
    with app.app_context():
        seed_categories()

    click.echo("Database reset successfully!")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=5000, help="Port to bind to")
@click.option("--debug/--no-debug", default=True, help="Enable debug mode")
def run(host, port, debug):
    """Run the development server."""
    from app import create_app

    app = create_app("development" if debug else "production")
    app.run(host=host, port=port, debug=debug)


@cli.command()
@click.argument("message")
def migrate(message):
    """Create a new database migration."""
    click.echo(f"Creating migration: {message}")
    os.system(f'alembic revision --autogenerate -m "{message}"')
    click.echo("Migration created successfully!")


@cli.command()
def upgrade():
    """Upgrade database to latest migration."""
    click.echo("Upgrading database...")
    os.system("alembic upgrade head")
    click.echo("Database upgraded successfully!")


@cli.command()
def downgrade():
    """Downgrade database by one migration."""
    if not click.confirm("This will revert the last migration. Are you sure?"):
        click.echo("Aborted.")
        return

    click.echo("Downgrading database...")
    os.system("alembic downgrade -1")
    click.echo("Database downgraded successfully!")


@cli.command()
def routes():
    """List all available routes."""
    from app import create_app

    app = create_app()

    click.echo("\nAvailable routes:\n")

    # Group routes by blueprint
    routes_by_blueprint = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint != "static":
            blueprint = rule.endpoint.split(".")[0] if "." in rule.endpoint else "main"
            if blueprint not in routes_by_blueprint:
                routes_by_blueprint[blueprint] = []
            routes_by_blueprint[blueprint].append(rule)

    # Print routes grouped by blueprint
    for blueprint, rules in sorted(routes_by_blueprint.items()):
        click.echo(f"[{blueprint}]")
        for rule in sorted(rules, key=lambda r: r.rule):
            methods = ", ".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
            click.echo(f"  {methods:10} {rule.rule}")
        click.echo()


if __name__ == "__main__":
    cli()
