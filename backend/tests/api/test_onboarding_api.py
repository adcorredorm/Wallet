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
    # "test-jwt-secret-for-testing-only"
    token = jwt.encode(payload, "test-jwt-secret-for-testing-only", algorithm="HS256")
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

    def test_seed_categories_have_seed_offline_id_prefix(self, client, app):
        """
        Categories created by seed must have offline_id starting with 'seed-'.
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
            (cat.offline_id or "").startswith("seed-") for cat in categories
        )

    def test_seed_creates_exact_account_count(self, client, app):
        """Seed must create exactly 3 accounts."""
        from app.extensions import db
        from app.models.account import Account
        from uuid import UUID

        user_id = str(uuid4())
        user_id_uuid = UUID(user_id)
        _create_test_user(app, user_id)
        headers = _auth_headers(user_id)

        resp = client.post("/api/v1/onboarding/seed", headers=headers)
        assert resp.status_code == 201

        with app.app_context():
            count = db.session.execute(
                db.select(db.func.count()).select_from(Account).where(
                    Account.user_id == user_id_uuid
                )
            ).scalar()

        assert count == 3

    def test_seed_creates_exact_category_count(self, client, app):
        """Seed must create exactly 22 category rows: 2 income + 10 expense parents +
        10 subcategories across 4 parent categories (Alimentación×3, Vivienda×3,
        Transporte×3, Entretenimiento×1)."""
        from app.extensions import db
        from app.models.category import Category
        from uuid import UUID

        user_id = str(uuid4())
        user_id_uuid = UUID(user_id)
        _create_test_user(app, user_id)
        headers = _auth_headers(user_id)

        resp = client.post("/api/v1/onboarding/seed", headers=headers)
        assert resp.status_code == 201
        assert resp.get_json()["data"]["categories_created"] == 22

        with app.app_context():
            count = db.session.execute(
                db.select(db.func.count()).select_from(Category).where(
                    Category.user_id == user_id_uuid
                )
            ).scalar()

        assert count == 22

    def test_seed_income_categories_are_exactly_two(self, client, app):
        """Seed must produce exactly 2 income categories: Salario and Otros Ingresos."""
        from app.extensions import db
        from app.models.category import Category, CategoryType
        from uuid import UUID

        user_id = str(uuid4())
        user_id_uuid = UUID(user_id)
        _create_test_user(app, user_id)
        resp = client.post("/api/v1/onboarding/seed", headers=_auth_headers(user_id))
        assert resp.status_code == 201

        with app.app_context():
            income_cats = db.session.execute(
                db.select(Category).where(
                    Category.user_id == user_id_uuid,
                    Category.type == CategoryType.INCOME,
                    Category.parent_category_id.is_(None),
                )
            ).scalars().all()

        names = {c.name for c in income_cats}
        assert names == {"Salario", "Otros Ingresos"}

    def test_seed_dashboard_name_and_widget_count(self, client, app):
        """Dashboard must be named 'Seguimiento Mes' with exactly 4 widgets."""
        from app.extensions import db
        from app.models.dashboard import Dashboard
        from app.models.dashboard_widget import DashboardWidget
        from uuid import UUID

        user_id = str(uuid4())
        user_id_uuid = UUID(user_id)
        _create_test_user(app, user_id)
        resp = client.post("/api/v1/onboarding/seed", headers=_auth_headers(user_id))
        assert resp.status_code == 201

        with app.app_context():
            dashboard = db.session.execute(
                db.select(Dashboard).where(Dashboard.user_id == user_id_uuid)
            ).scalar_one()
            widget_count = db.session.execute(
                db.select(db.func.count()).select_from(DashboardWidget).where(
                    DashboardWidget.dashboard_id == dashboard.id
                )
            ).scalar()

        assert dashboard.name == "Seguimiento Mes"
        assert widget_count == 4

    def test_seed_widgets_use_last_30_days_time_range(self, client, app):
        """All 4 widgets must use time_range.value == 'last_30_days'."""
        from app.extensions import db
        from app.models.dashboard import Dashboard
        from app.models.dashboard_widget import DashboardWidget
        from uuid import UUID

        user_id = str(uuid4())
        user_id_uuid = UUID(user_id)
        _create_test_user(app, user_id)
        resp = client.post("/api/v1/onboarding/seed", headers=_auth_headers(user_id))
        assert resp.status_code == 201

        with app.app_context():
            dashboard = db.session.execute(
                db.select(Dashboard).where(Dashboard.user_id == user_id_uuid)
            ).scalar_one()
            widgets = db.session.execute(
                db.select(DashboardWidget).where(
                    DashboardWidget.dashboard_id == dashboard.id
                )
            ).scalars().all()

        for widget in widgets:
            assert widget.config["time_range"]["value"] == "last_30_days", (
                f"Widget '{widget.title}' has time_range "
                f"{widget.config['time_range']} instead of last_30_days"
            )

    def test_seed_widget_offline_ids_use_seed_prefix(self, client, app):
        """All widget offline_ids must start with 'seed-'."""
        from app.extensions import db
        from app.models.dashboard import Dashboard
        from app.models.dashboard_widget import DashboardWidget
        from uuid import UUID

        user_id = str(uuid4())
        user_id_uuid = UUID(user_id)
        _create_test_user(app, user_id)
        resp = client.post("/api/v1/onboarding/seed", headers=_auth_headers(user_id))
        assert resp.status_code == 201

        with app.app_context():
            dashboard = db.session.execute(
                db.select(Dashboard).where(Dashboard.user_id == user_id_uuid)
            ).scalar_one()
            widgets = db.session.execute(
                db.select(DashboardWidget).where(
                    DashboardWidget.dashboard_id == dashboard.id
                )
            ).scalars().all()

        for widget in widgets:
            assert (widget.offline_id or "").startswith("seed-"), (
                f"Widget '{widget.title}' has offline_id '{widget.offline_id}'"
            )
