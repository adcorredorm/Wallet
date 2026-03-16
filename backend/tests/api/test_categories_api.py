"""
API-level tests for the categories blueprint.

These tests use the Flask test client with the CategoryService mocked at the
module boundary so no database connection is required.  Only the route logic
and HTTP layer are exercised here; service business logic is covered in the
unit tests under tests/unit/services/.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, ANY
from uuid import uuid4

import jwt

from app.models.category import Category, CategoryType
from app.utils.exceptions import NotFoundError, BusinessRuleError

_TEST_USER_ID = uuid4()
_JWT_SECRET = "test-jwt-secret-for-testing-only"
# Dummy header used when verify_jwt is patched to bypass real JWT validation
_H = {"Authorization": "Bearer dummy"}


def _auth_headers(user_id=None) -> dict:
    uid = user_id or _TEST_USER_ID
    payload = {
        "sub": str(uid),
        "email": "cat-test@example.com",
        "name": "Cat Test",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, _JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


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
    mock.offline_id = None
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
def bypass_auth():
    """
    Bypass JWT authentication for all tests in this module.

    Patches verify_jwt so it always returns a valid payload containing the
    test user's UUID.  This allows the @require_auth decorator to succeed
    without a real JWT token, provided the request includes *any* Bearer
    token (even a dummy one).

    All client calls in this module pass a dummy Authorization header.
    """
    payload = {
        "sub": str(_TEST_USER_ID),
        "email": "cat-test@example.com",
        "name": "Cat Test",
    }
    with patch("app.utils.auth.verify_jwt", return_value=payload):
        yield


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

        response = client.get("/api/v1/categories", headers=_H)

        assert response.status_code == 200
        mock_category_service.get_all.assert_called_once_with(
            user_id=_TEST_USER_ID, type=None, include_archived=False
        )

    def test_include_archived_true_passes_flag(
        self, client, mock_category_service
    ):
        """Should forward include_archived=True to the service."""
        mock_category_service.get_all.return_value = []

        response = client.get("/api/v1/categories?include_archived=true", headers=_H)

        assert response.status_code == 200
        mock_category_service.get_all.assert_called_once_with(
            user_id=_TEST_USER_ID, type=None, include_archived=True
        )

    def test_include_archived_false_explicit(
        self, client, mock_category_service
    ):
        """Explicitly passing include_archived=false should pass False to service."""
        mock_category_service.get_all.return_value = []

        client.get("/api/v1/categories?include_archived=false", headers=_H)

        mock_category_service.get_all.assert_called_once_with(
            user_id=_TEST_USER_ID, type=None, include_archived=False
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

        response = client.delete(f"/api/v1/categories/{category_id}", headers=_H)
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

        client.delete(f"/api/v1/categories/{category_id}", headers=_H)

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

        response = client.delete(f"/api/v1/categories/{category_id}", headers=_H)

        assert response.status_code == 404

    def test_archive_does_not_call_hard_delete(
        self, client, mock_category_service
    ):
        """Soft-delete route must NOT invoke hard_delete."""
        category_id = uuid4()
        mock_category_service.archive.return_value = None

        client.delete(f"/api/v1/categories/{category_id}", headers=_H)

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

        response = client.delete(f"/api/v1/categories/{category_id}/permanent", headers=_H)

        assert response.status_code == 200

    def test_hard_delete_success_message_contains_permanentemente(
        self, client, mock_category_service
    ):
        """Success message should reference permanent deletion."""
        category_id = uuid4()
        mock_category_service.hard_delete.return_value = None

        response = client.delete(f"/api/v1/categories/{category_id}/permanent", headers=_H)
        body = response.get_json()

        assert "permanentemente" in body["message"].lower()

    def test_hard_delete_calls_service_with_correct_id(
        self, client, mock_category_service
    ):
        """The UUID from the URL path must be forwarded to hard_delete."""
        category_id = uuid4()
        mock_category_service.hard_delete.return_value = None

        client.delete(f"/api/v1/categories/{category_id}/permanent", headers=_H)

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

        response = client.delete(f"/api/v1/categories/{category_id}/permanent", headers=_H)

        assert response.status_code == 404

    def test_hard_delete_returns_422_when_business_rule_error(
        self, client, mock_category_service
    ):
        """Should return HTTP 422 when a BusinessRuleError is raised (e.g. has subcategories)."""
        category_id = uuid4()
        mock_category_service.hard_delete.side_effect = BusinessRuleError(
            "No se puede eliminar una categoria con subcategorias"
        )

        response = client.delete(f"/api/v1/categories/{category_id}/permanent", headers=_H)
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

        response = client.delete(f"/api/v1/categories/{category_id}/permanent", headers=_H)

        assert response.status_code == 422

    def test_hard_delete_does_not_call_archive(
        self, client, mock_category_service
    ):
        """Permanent-delete route must NOT invoke the archive method."""
        category_id = uuid4()
        mock_category_service.hard_delete.return_value = None

        client.delete(f"/api/v1/categories/{category_id}/permanent", headers=_H)

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
            headers=_H,
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
            headers=_H,
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
            headers=_H,
        )

        call_kwargs = mock_category_service.update.call_args[1]
        assert call_kwargs.get("active") is None
