"""
Dashboard API endpoints for consolidated views.

All routes are protected by @require_auth. The authenticated user's UUID is
read from g.current_user_id (injected by the decorator) and forwarded to
every service call so data is always scoped to the current user.
"""

from flask import Blueprint, g, request

from app.services import DashboardService
from app.utils.auth import require_auth
from app.utils.responses import success_response, error_response

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")
dashboard_service = DashboardService()


@dashboard_bp.route("", methods=["GET"])
@require_auth
def get_dashboard():
    """
    Get complete dashboard data for the authenticated user.

    Query Parameters:
        month (int): Month for summary (1-12, defaults to current month)
        year (int): Year for summary (defaults to current year)

    Returns:
        200: Complete dashboard data (net worth, monthly summary, recent activity)
        400: Invalid parameters
        401: Authentication required
        500: Internal server error
    """
    try:
        month = request.args.get("month", type=int)
        year = request.args.get("year", type=int)

        if month and (month < 1 or month > 12):
            return error_response("Mes debe estar entre 1 y 12", status_code=400)

        data = dashboard_service.get_dashboard_data(
            user_id=g.current_user_id, month=month, year=year
        )

        return success_response(data=data)

    except Exception as e:
        return error_response(f"Error al obtener dashboard: {str(e)}", status_code=500)


@dashboard_bp.route("/net-worth", methods=["GET"])
@require_auth
def get_net_worth():
    """
    Get net worth (total balances by currency) for the authenticated user.

    Returns:
        200: Net worth data
        401: Authentication required
        500: Internal server error
    """
    try:
        data = dashboard_service.get_net_worth(user_id=g.current_user_id)
        return success_response(data=data)

    except Exception as e:
        return error_response(f"Error al calcular patrimonio neto: {str(e)}", status_code=500)


@dashboard_bp.route("/summary", methods=["GET"])
@require_auth
def get_monthly_summary():
    """
    Get monthly summary of income and expenses for the authenticated user.

    Query Parameters:
        month (int): Month (1-12, defaults to current month)
        year (int): Year (defaults to current year)

    Returns:
        200: Monthly summary data
        400: Invalid parameters
        401: Authentication required
        500: Internal server error
    """
    try:
        from datetime import date

        today = date.today()
        month = request.args.get("month", type=int, default=today.month)
        year = request.args.get("year", type=int, default=today.year)

        if month < 1 or month > 12:
            return error_response("Mes debe estar entre 1 y 12", status_code=400)

        data = dashboard_service.get_monthly_summary(
            user_id=g.current_user_id, month=month, year=year
        )

        return success_response(data=data)

    except Exception as e:
        return error_response(f"Error al obtener resumen mensual: {str(e)}", status_code=500)


@dashboard_bp.route("/recent-activity", methods=["GET"])
@require_auth
def get_recent_activity():
    """
    Get recent activity (transactions and transfers) for the authenticated user.

    Query Parameters:
        limit (int): Maximum number of activities (default: 10, max: 50)

    Returns:
        200: Recent activity data
        401: Authentication required
        500: Internal server error
    """
    try:
        limit = min(request.args.get("limit", type=int, default=10), 50)

        data = dashboard_service.get_recent_activity(
            user_id=g.current_user_id, limit=limit
        )

        return success_response(data=data)

    except Exception as e:
        return error_response(f"Error al obtener actividad reciente: {str(e)}", status_code=500)
