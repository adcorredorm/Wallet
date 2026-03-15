"""
Tests for POST /api/v1/onboarding/seed endpoint.

The endpoint creates predefined accounts and categories for a new user.
It requires @require_auth and returns 409 if the user already has accounts.
"""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(user_id: str | None = None) -> dict:
    """
    Build Authorization header with a minimal valid JWT.

    Uses the test app's JWT_SECRET to produce a real token so the decorator
    validates it without a network call.
    """
    import jwt
    from datetime import datetime, timedelta

    user_id = user_id or str(uuid4())

    payload = {
        "sub": user_id,
        "email": "test@example.com",
        "name": "Test User",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }

    # TestingConfig inherits JWT_SECRET from Config base:
    # "dev-jwt-secret-change-in-production"
    token = jwt.encode(payload, "dev-jwt-secret-change-in-production", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def _create_test_user(app, user_id: str) -> None:
    """Create a User record in the test DB so FK constraints pass."""
    from app.extensions import db
    from app.models.user import User
    from uuid import UUID

    with app.app_context():
        user = User(
            id=UUID(user_id),
            google_id=f"google-{user_id}",
            email=f"{user_id[:8]}@test.com",
            name="Test User",
        )
        db.session.add(user)
        db.session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOnboardingSeed:
    """Tests for POST /api/v1/onboarding/seed."""

    def test_requires_auth(self, client):
        """Should return 401 when no token is provided."""
        resp = client.post("/api/v1/onboarding/seed")
        assert resp.status_code == 401

    def test_seed_creates_accounts_and_categories(self, client, app):
        """
        Should create seed data and return counts.

        Creates a User record first so FK constraints pass, then calls seed.
        """
        user_id = str(uuid4())
        _create_test_user(app, user_id)
        headers = _auth_headers(user_id)

        resp = client.post("/api/v1/onboarding/seed", headers=headers)
        data = resp.get_json()

        assert resp.status_code == 201, data
        assert data["success"] is True
        assert "accounts_created" in data["data"]
        assert "categories_created" in data["data"]
        assert "dashboard_created" in data["data"]
        assert data["data"]["accounts_created"] > 0
        assert data["data"]["categories_created"] > 0
        assert data["data"]["dashboard_created"] is True

    def test_seed_is_idempotent_returns_409_if_user_has_accounts(self, client, app):
        """
        Should return 409 when the user already has at least one account.

        The guard fires after the first seed call. We call it twice and verify
        the second call returns 409.
        """
        user_id = str(uuid4())
        _create_test_user(app, user_id)
        headers = _auth_headers(user_id)

        # First call should succeed
        resp1 = client.post("/api/v1/onboarding/seed", headers=headers)
        assert resp1.status_code == 201

        # Second call should be rejected
        resp2 = client.post("/api/v1/onboarding/seed", headers=headers)
        assert resp2.status_code == 409
        data = resp2.get_json()
        assert data["success"] is False

    def test_seed_accounts_have_auto_generated_tag(self, client, app):
        """
        Accounts created by seed must have 'auto-generated' in their tags.
        """
        from app.extensions import db
        from app.models.account import Account

        user_id = str(uuid4())
        from uuid import UUID
        user_id_uuid = UUID(user_id)

        _create_test_user(app, user_id)
        headers = _auth_headers(user_id)
        resp = client.post("/api/v1/onboarding/seed", headers=headers)
        assert resp.status_code == 201

        with app.app_context():
            accounts = db.session.execute(
                db.select(Account).where(Account.user_id == user_id_uuid)
            ).scalars().all()

        assert all("auto-generated" in (acc.tags or []) for acc in accounts)

    def test_seed_categories_have_seed_client_id_prefix(self, client, app):
        """
        Categories created by seed must have client_id starting with 'seed-'.
        """
        from app.extensions import db
        from app.models.category import Category

        user_id = str(uuid4())
        from uuid import UUID
        user_id_uuid = UUID(user_id)

        _create_test_user(app, user_id)
        headers = _auth_headers(user_id)
        resp = client.post("/api/v1/onboarding/seed", headers=headers)
        assert resp.status_code == 201

        with app.app_context():
            categories = db.session.execute(
                db.select(Category).where(Category.user_id == user_id_uuid)
            ).scalars().all()

        assert all(
            (cat.client_id or "").startswith("seed-") for cat in categories
        )
