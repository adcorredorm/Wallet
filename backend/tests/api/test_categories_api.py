"""
API-level tests for the categories blueprint.

These tests use the Flask test client with the CategoryService mocked at the
module boundary so no database connection is required.  Only the route logic
and HTTP layer are exercised here; service business logic is covered in the
unit tests under tests/unit/services/.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.models.category import Category, CategoryType
from app.utils.exceptions import NotFoundError, BusinessRuleError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_category_mock(
    *,
    active: bool = True,
    has_subcategories: bool = False,
) -> MagicMock:
    """
    Build a lightweight mock that satisfies CategoryResponse.model_validate.

    Args:
        active: Value for the active flag.
        has_subcategories: When True, subcategories.count() returns 1.

    Returns:
        MagicMock configured to mimic a Category ORM instance.
    """
    from datetime import datetime, timezone

    mock = MagicMock(spec=Category)
    mock.id = uuid4()
    mock.name = "Alimentación"
    mock.type = CategoryType.EXPENSE
    mock.icon = "food-icon"
    mock.color = "#FF5733"
    mock.parent_category_id = None
    mock.active = active
    mock.client_id = None
    mock.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    mock.updated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    mock.subcategories = MagicMock()
    mock.subcategories.count.return_value = 1 if has_subcategories else 0
    mock.subcategories.all.return_value = []

    mock.transactions = MagicMock()
    mock.transactions.count.return_value = 0

    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_category_service():
    """
    Patch the CategoryService instance used by the categories blueprint for
    every test in this module.

    Yields:
        The MagicMock replacing the module-level ``category_service`` object.
    """
    with patch("app.api.categories.category_service") as mock_svc:
        yield mock_svc


# ---------------------------------------------------------------------------
# GET /api/v1/categories
# ---------------------------------------------------------------------------

class TestListCategories:
    """Tests for GET /api/v1/categories."""

    def test_returns_active_categories_by_default(
        self, client, mock_category_service
    ):
        """Should call get_all with include_archived=False when param is absent."""
        cat = _make_category_mock()
        mock_category_service.get_all.return_value = [cat]

        response = client.get("/api/v1/categories")

        assert response.status_code == 200
        mock_category_service.get_all.assert_called_once_with(
            type=None, include_archived=False
        )

    def test_include_archived_true_passes_flag(
        self, client, mock_category_service
    ):
        """Should forward include_archived=True to the service."""
        mock_category_service.get_all.return_value = []

        response = client.get("/api/v1/categories?include_archived=true")

        assert response.status_code == 200
        mock_category_service.get_all.assert_called_once_with(
            type=None, include_archived=True
        )

    def test_include_archived_false_explicit(
        self, client, mock_category_service
    ):
        """Explicitly passing include_archived=false should pass False to service."""
        mock_category_service.get_all.return_value = []

        client.get("/api/v1/categories?include_archived=false")

        mock_category_service.get_all.assert_called_once_with(
            type=None, include_archived=False
        )


# ---------------------------------------------------------------------------
# DELETE /api/v1/categories/:id  (archive / soft delete)
# ---------------------------------------------------------------------------

class TestArchiveCategory:
    """Tests for DELETE /api/v1/categories/:id — soft delete / archive."""

    def test_archive_returns_200_with_archivada_message(
        self, client, mock_category_service
    ):
        """Should return 200 and the 'archivada' success message."""
        category_id = uuid4()
        mock_category_service.archive.return_value = None

        response = client.delete(f"/api/v1/categories/{category_id}")
        body = response.get_json()

        assert response.status_code == 200
        assert "archivada" in body["message"].lower()
        mock_category_service.archive.assert_called_once()

    def test_archive_calls_service_with_correct_id(
        self, client, mock_category_service
    ):
        """The UUID from the URL path must be forwarded to the service."""
        category_id = uuid4()
        mock_category_service.archive.return_value = None

        client.delete(f"/api/v1/categories/{category_id}")

        call_args = mock_category_service.archive.call_args
        assert str(call_args[0][0]) == str(category_id)

    def test_archive_returns_404_when_not_found(
        self, client, mock_category_service
    ):
        """Should propagate NotFoundError as HTTP 404."""
        category_id = uuid4()
        mock_category_service.archive.side_effect = NotFoundError(
            "Category", str(category_id)
        )

        response = client.delete(f"/api/v1/categories/{category_id}")

        assert response.status_code == 404

    def test_archive_does_not_call_hard_delete(
        self, client, mock_category_service
    ):
        """Soft-delete route must NOT invoke hard_delete."""
        category_id = uuid4()
        mock_category_service.archive.return_value = None

        client.delete(f"/api/v1/categories/{category_id}")

        mock_category_service.hard_delete.assert_not_called()


# ---------------------------------------------------------------------------
# DELETE /api/v1/categories/:id/permanent  (hard delete)
# ---------------------------------------------------------------------------

class TestHardDeleteCategory:
    """Tests for DELETE /api/v1/categories/:id/permanent — permanent delete."""

    def test_hard_delete_returns_200_on_success(
        self, client, mock_category_service
    ):
        """Should return HTTP 200 when hard_delete succeeds."""
        category_id = uuid4()
        mock_category_service.hard_delete.return_value = None

        response = client.delete(f"/api/v1/categories/{category_id}/permanent")

        assert response.status_code == 200

    def test_hard_delete_success_message_contains_permanentemente(
        self, client, mock_category_service
    ):
        """Success message should reference permanent deletion."""
        category_id = uuid4()
        mock_category_service.hard_delete.return_value = None

        response = client.delete(f"/api/v1/categories/{category_id}/permanent")
        body = response.get_json()

        assert "permanentemente" in body["message"].lower()

    def test_hard_delete_calls_service_with_correct_id(
        self, client, mock_category_service
    ):
        """The UUID from the URL path must be forwarded to hard_delete."""
        category_id = uuid4()
        mock_category_service.hard_delete.return_value = None

        client.delete(f"/api/v1/categories/{category_id}/permanent")

        call_args = mock_category_service.hard_delete.call_args
        assert str(call_args[0][0]) == str(category_id)

    def test_hard_delete_returns_404_when_not_found(
        self, client, mock_category_service
    ):
        """Should return HTTP 404 when the category does not exist."""
        category_id = uuid4()
        mock_category_service.hard_delete.side_effect = NotFoundError(
            "Category", str(category_id)
        )

        response = client.delete(f"/api/v1/categories/{category_id}/permanent")

        assert response.status_code == 404

    def test_hard_delete_returns_422_when_business_rule_error(
        self, client, mock_category_service
    ):
        """Should return HTTP 422 when a BusinessRuleError is raised (e.g. has subcategories)."""
        category_id = uuid4()
        mock_category_service.hard_delete.side_effect = BusinessRuleError(
            "No se puede eliminar una categoria con subcategorias"
        )

        response = client.delete(f"/api/v1/categories/{category_id}/permanent")
        body = response.get_json()

        assert response.status_code == 422
        assert "subcategorias" in body["message"].lower()

    def test_hard_delete_returns_422_when_has_transactions(
        self, client, mock_category_service
    ):
        """Should return HTTP 422 when the category has linked transactions."""
        category_id = uuid4()
        mock_category_service.hard_delete.side_effect = BusinessRuleError(
            "No se puede eliminar una categoria con transacciones"
        )

        response = client.delete(f"/api/v1/categories/{category_id}/permanent")

        assert response.status_code == 422

    def test_hard_delete_does_not_call_archive(
        self, client, mock_category_service
    ):
        """Permanent-delete route must NOT invoke the archive method."""
        category_id = uuid4()
        mock_category_service.hard_delete.return_value = None

        client.delete(f"/api/v1/categories/{category_id}/permanent")

        mock_category_service.archive.assert_not_called()


# ---------------------------------------------------------------------------
# PUT /api/v1/categories/:id  (active field passthrough)
# ---------------------------------------------------------------------------

class TestUpdateCategoryActive:
    """Tests for PUT /api/v1/categories/:id — active field forwarding."""

    def test_put_passes_active_false_to_service(
        self, client, mock_category_service
    ):
        """Setting active=False in the body must reach category_service.update."""
        category_id = uuid4()
        mock_category_service.get_by_id.return_value = None  # skip LWW path
        cat = _make_category_mock(active=False)
        mock_category_service.update.return_value = cat

        response = client.put(
            f"/api/v1/categories/{category_id}",
            data=json.dumps({"active": False}),
            content_type="application/json",
        )

        assert response.status_code == 200
        call_kwargs = mock_category_service.update.call_args[1]
        assert call_kwargs.get("active") is False

    def test_put_passes_active_true_to_service(
        self, client, mock_category_service
    ):
        """Setting active=True in the body must reach category_service.update."""
        category_id = uuid4()
        cat = _make_category_mock(active=True)
        mock_category_service.update.return_value = cat

        response = client.put(
            f"/api/v1/categories/{category_id}",
            data=json.dumps({"active": True}),
            content_type="application/json",
        )

        assert response.status_code == 200
        call_kwargs = mock_category_service.update.call_args[1]
        assert call_kwargs.get("active") is True

    def test_put_active_none_when_omitted(
        self, client, mock_category_service
    ):
        """When active is not in the body, None must be forwarded to the service."""
        category_id = uuid4()
        cat = _make_category_mock()
        mock_category_service.update.return_value = cat

        client.put(
            f"/api/v1/categories/{category_id}",
            data=json.dumps({"name": "Renamed"}),
            content_type="application/json",
        )

        call_kwargs = mock_category_service.update.call_args[1]
        assert call_kwargs.get("active") is None
