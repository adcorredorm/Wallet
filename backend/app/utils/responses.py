"""
Response helper functions for consistent API responses.
"""

from typing import Any, Optional
from flask import jsonify
import math


def success_response(
    data: Any = None, message: Optional[str] = None, status_code: int = 200
) -> tuple[dict, int]:
    """
    Create a successful API response.

    Args:
        data: Response data payload
        message: Optional success message
        status_code: HTTP status code (default 200)

    Returns:
        Tuple of (response dict, status code)
    """
    response = {"success": True}

    if message:
        response["message"] = message

    if data is not None:
        response["data"] = data

    return response, status_code


def error_response(
    message: str, status_code: int = 400, errors: Optional[dict] = None
) -> tuple[dict, int]:
    """
    Create an error API response.

    Args:
        message: Error message
        status_code: HTTP status code (default 400)
        errors: Optional detailed error information

    Returns:
        Tuple of (response dict, status code)
    """
    response = {"success": False, "message": message}

    if errors:
        response["errors"] = errors

    return response, status_code


def paginated_response(
    items: list[Any], total: int, page: int, page_size: int, status_code: int = 200
) -> tuple[dict, int]:
    """
    Create a paginated API response.

    Args:
        items: List of items for current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        page_size: Number of items per page
        status_code: HTTP status code (default 200)

    Returns:
        Tuple of (response dict, status code)
    """
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    response = {
        "success": True,
        "data": {
            "items": items,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            },
        },
    }

    return response, status_code
