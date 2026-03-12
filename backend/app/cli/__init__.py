"""
CLI commands package.

This package registers all Flask CLI blueprints. Each sub-module exposes a
Blueprint whose `cli` group adds commands to the `flask` runner.
"""

from flask import Flask

from app.cli.rates import rates_bp


def register_cli(app: Flask) -> None:
    """
    Register all CLI blueprints with the Flask application.

    Commands become available as sub-commands of their blueprint name, e.g.
    ``flask rates update``.

    Args:
        app: Flask application instance.
    """
    app.register_blueprint(rates_bp)
