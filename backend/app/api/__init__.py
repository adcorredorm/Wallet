"""
API blueprints package.

This package contains all Flask blueprints for the API endpoints.
"""

from flask import Flask

from app.api.accounts import accounts_bp
from app.api.auth import auth_bp
from app.api.categories import categories_bp
from app.api.transactions import transactions_bp
from app.api.transfers import transfers_bp
from app.api.dashboard import dashboard_bp
from app.api.exchange_rates import exchange_rates_bp
from app.api.onboarding import onboarding_bp
from app.api.settings import settings_bp
from app.api.dashboards import dashboards_bp


def register_blueprints(app: Flask) -> None:
    """
    Register all API blueprints with the Flask application.

    Args:
        app: Flask application instance
    """
    app.register_blueprint(auth_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(transfers_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(exchange_rates_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(dashboards_bp)
