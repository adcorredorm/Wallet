"""
API blueprints package.

This package contains all Flask blueprints for the API endpoints.
"""

from flask import Flask

from app.api.accounts import accounts_bp
from app.api.categories import categories_bp
from app.api.transactions import transactions_bp
from app.api.transfers import transfers_bp
from app.api.dashboard import dashboard_bp


def register_blueprints(app: Flask) -> None:
    """
    Register all API blueprints with the Flask application.

    Args:
        app: Flask application instance
    """
    app.register_blueprint(accounts_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(transfers_bp)
    app.register_blueprint(dashboard_bp)
