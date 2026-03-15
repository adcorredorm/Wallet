"""
Wallet Backend Application Factory.

This module provides the application factory for creating Flask instances
with all necessary extensions and blueprints registered.
"""

from flask import Flask
from flask_cors import CORS

from app.config import get_config
from app.extensions import db, migrate


def create_app(config_name: str = "development") -> Flask:
    """
    Application factory for creating Flask instances.

    Args:
        config_name: Configuration environment name (development, testing, production)

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(
        app,
        origins=app.config.get("CORS_ORIGINS", []),
        # X-Sync-Cursor must be explicitly exposed so the browser can read it
        # in cross-origin contexts (CORS safe-list excludes custom headers).
        # If-Sync-Cursor must be allowed so the preflight passes.
        expose_headers=["X-Sync-Cursor"],
        allow_headers=["Content-Type", "Authorization", "If-Sync-Cursor"],
    )

    # Register blueprints
    from app.api import register_blueprints
    register_blueprints(app)

    # Register CLI commands
    from app.cli import register_cli
    register_cli(app)

    # Health check endpoint
    @app.route("/health")
    def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "wallet-api"}, 200

    return app
