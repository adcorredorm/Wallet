"""
Tests for RecurringRule: model instantiation, service CRUD, and API endpoints.

Service tests use the real database via the `app` fixture (requires db:5432).
API tests mock the service layer and run without a database connection.
"""

import json
import base64
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4, UUID

import jwt
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEST_USER_ID = uuid4()
_JWT_SECRET = "test-jwt-secret-for-testing-only"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _auth_headers(user_id=None) -> dict:
    uid = user_id or _TEST_USER_ID
    payload = {
        "sub": str(uid),
        "email": "rr-test@example.com",
        "name": "RR Test",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, _JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def _cursor(dt: datetime) -> str:
    payload = json.dumps({"t": dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z", "v": 1})
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def future_cursor() -> str:
    return _cursor(datetime.utcnow() + timedelta(hours=1))


def past_cursor() -> str:
    return _cursor(datetime.utcnow() - timedelta(hours=1))


# ---------------------------------------------------------------------------
# DB fixture: ensure test user exists
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def ensure_test_user(app):
    from app.extensions import db
    from app.models.user import User

    with app.app_context():
        existing = db.session.get(User, _TEST_USER_ID)
        if existing is None:
            user = User(
                id=_TEST_USER_ID,
                google_id=f"google-rr-{str(_TEST_USER_ID)[:8]}",
                email="rr-test@example.com",
                name="RR Test",
            )
            db.session.add(user)
            db.session.commit()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestRecurringRuleModel:
    """Verify model instantiation and enum values without hitting the DB."""

    def test_frequency_enum_values(self):
        from app.models.recurring_rule import RecurringFrequency
        assert RecurringFrequency.DAILY.value == "daily"
        assert RecurringFrequency.WEEKLY.value == "weekly"
        assert RecurringFrequency.MONTHLY.value == "monthly"
        assert RecurringFrequency.YEARLY.value == "yearly"

    def test_status_enum_values(self):
        from app.models.recurring_rule import RecurringRuleStatus
        assert RecurringRuleStatus.ACTIVE.value == "active"
        assert RecurringRuleStatus.PAUSED.value == "paused"
        assert RecurringRuleStatus.COMPLETED.value == "completed"

    def test_model_repr(self, app):
        from app.models.recurring_rule import RecurringRule, RecurringFrequency, RecurringRuleStatus
        from app.models.transaction import TransactionType
        with app.app_context():
            rule = RecurringRule(
                user_id=_TEST_USER_ID,
                title="Netflix",
                type=TransactionType.EXPENSE,
                amount=Decimal("15.99"),
                account_id=uuid4(),
                category_id=uuid4(),
                frequency=RecurringFrequency.MONTHLY,
                interval=1,
                start_date=date.today(),
                next_occurrence_date=date.today(),
                status=RecurringRuleStatus.ACTIVE,
                tags=[],
                requires_confirmation=False,
                occurrences_created=0,
            )
            r = repr(rule)
            assert "Netflix" in r
            assert "monthly" in r
            assert "active" in r


# ---------------------------------------------------------------------------
# Service tests (require real DB)
# ---------------------------------------------------------------------------

class TestRecurringRuleService:
    """Service CRUD operations against the test database."""

    @pytest.fixture
    def account_id(self, app):
        from app.extensions import db
        from app.models.account import Account, AccountType
        with app.app_context():
            acc = Account(
                user_id=_TEST_USER_ID,
                name=f"Acct-{uuid4().hex[:6]}",
                type=AccountType.DEBIT,
                currency="MXN",
                active=True,
            )
            db.session.add(acc)
            db.session.commit()
            return acc.id

    @pytest.fixture
    def category_id(self, app):
        from app.extensions import db
        from app.models.category import Category, CategoryType
        with app.app_context():
            cat = Category(
                user_id=_TEST_USER_ID,
                name=f"Cat-{uuid4().hex[:6]}",
                type=CategoryType.EXPENSE,
                active=True,
            )
            db.session.add(cat)
            db.session.commit()
            return cat.id

    def _make_rule(self, service, account_id, category_id, **overrides):
        defaults = dict(
            user_id=_TEST_USER_ID,
            offline_id=f"test-{uuid4().hex}",
            title="Netflix",
            type="income",
            amount=Decimal("15.99"),
            account_id=account_id,
            category_id=category_id,
            frequency="monthly",
            start_date=date(2026, 1, 1),
            next_occurrence_date=date(2026, 4, 1),
        )
        defaults.update(overrides)
        return service.create(**defaults)

    def test_create_returns_rule(self, app, account_id, category_id):
        from app.services.recurring_rule import RecurringRuleService
        with app.app_context():
            service = RecurringRuleService()
            rule = self._make_rule(service, account_id, category_id)
            assert rule.id is not None
            assert rule.title == "Netflix"
            assert rule.status.value == "active"
            assert rule.occurrences_created == 0

    def test_create_idempotent_on_offline_id(self, app, account_id, category_id):
        from app.services.recurring_rule import RecurringRuleService
        with app.app_context():
            service = RecurringRuleService()
            oid = f"idem-{uuid4().hex}"
            r1 = self._make_rule(service, account_id, category_id, offline_id=oid)
            r2 = self._make_rule(service, account_id, category_id, offline_id=oid)
            assert r1.id == r2.id

    def test_get_by_id_returns_rule(self, app, account_id, category_id):
        from app.services.recurring_rule import RecurringRuleService
        with app.app_context():
            service = RecurringRuleService()
            created = self._make_rule(service, account_id, category_id)
            fetched = service.get_by_id(created.id, _TEST_USER_ID)
            assert fetched.id == created.id

    def test_get_by_id_raises_for_wrong_user(self, app, account_id, category_id):
        from app.services.recurring_rule import RecurringRuleService
        from app.utils.exceptions import NotFoundError
        with app.app_context():
            service = RecurringRuleService()
            rule = self._make_rule(service, account_id, category_id)
            with pytest.raises(NotFoundError):
                service.get_by_id(rule.id, uuid4())

    def test_get_filtered_by_status(self, app, account_id, category_id):
        from app.services.recurring_rule import RecurringRuleService
        with app.app_context():
            service = RecurringRuleService()
            self._make_rule(service, account_id, category_id, status="active")
            self._make_rule(service, account_id, category_id, status="paused")
            active_rules, _ = service.get_filtered(
                user_id=_TEST_USER_ID, status="active"
            )
            for r in active_rules:
                assert r.status.value == "active"

    def test_get_filtered_with_future_updated_since_returns_empty(self, app, account_id, category_id):
        from app.services.recurring_rule import RecurringRuleService
        with app.app_context():
            service = RecurringRuleService()
            self._make_rule(service, account_id, category_id)
            future = datetime.utcnow() + timedelta(hours=1)
            rules, total = service.get_filtered(
                user_id=_TEST_USER_ID, updated_since=future
            )
            assert total == 0
            assert rules == []

    def test_update_title_and_status(self, app, account_id, category_id):
        from app.services.recurring_rule import RecurringRuleService
        with app.app_context():
            service = RecurringRuleService()
            rule = self._make_rule(service, account_id, category_id)
            updated = service.update(
                rule.id,
                _TEST_USER_ID,
                title="Spotify",
                status="paused",
            )
            assert updated.title == "Spotify"
            assert updated.status.value == "paused"

    def test_delete_removes_rule(self, app, account_id, category_id):
        from app.services.recurring_rule import RecurringRuleService
        from app.utils.exceptions import NotFoundError
        with app.app_context():
            service = RecurringRuleService()
            rule = self._make_rule(service, account_id, category_id)
            service.delete(rule.id, _TEST_USER_ID)
            with pytest.raises(NotFoundError):
                service.get_by_id(rule.id, _TEST_USER_ID)


# ---------------------------------------------------------------------------
# Helpers for API tests
# ---------------------------------------------------------------------------

def _make_mock_rule(rule_id=None):
    """Build a minimal mock compatible with RecurringRuleResponse.model_validate."""
    from app.models.recurring_rule import RecurringFrequency, RecurringRuleStatus
    from app.models.transaction import TransactionType

    rule = MagicMock()
    rule.id = rule_id or uuid4()
    rule.offline_id = f"offline-{uuid4().hex[:8]}"
    rule.user_id = _TEST_USER_ID
    rule.title = "Netflix"
    rule.type = TransactionType.EXPENSE
    rule.amount = Decimal("15.99")
    rule.account_id = uuid4()
    rule.category_id = uuid4()
    rule.description = None
    rule.tags = []
    rule.requires_confirmation = False
    rule.frequency = RecurringFrequency.MONTHLY
    rule.interval = 1
    rule.day_of_month = None
    rule.start_date = date(2026, 1, 1)
    rule.end_date = None
    rule.max_occurrences = None
    rule.occurrences_created = 0
    rule.next_occurrence_date = date(2026, 4, 1)
    rule.status = RecurringRuleStatus.ACTIVE
    rule.created_at = datetime.utcnow()
    rule.updated_at = datetime.utcnow()
    return rule


def _valid_create_payload() -> dict:
    return {
        "offline_id": f"test-{uuid4().hex}",
        "title": "Netflix",
        "type": "expense",
        "amount": "15.99",
        "account_id": str(uuid4()),
        "category_id": str(uuid4()),
        "frequency": "monthly",
        "interval": 1,
        "start_date": "2026-01-01",
        "next_occurrence_date": "2026-04-01",
    }


# ---------------------------------------------------------------------------
# API tests — GET /api/v1/recurring-rules
# ---------------------------------------------------------------------------

class TestListRecurringRules:
    """GET /api/v1/recurring-rules"""

    def test_returns_200_with_paginated_rules(self, client):
        mock_rule = _make_mock_rule()
        with patch("app.api.recurring_rules.recurring_rule_service") as svc:
            svc.get_filtered.return_value = ([mock_rule], 1)
            resp = client.get(
                "/api/v1/recurring-rules",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "X-Sync-Cursor" in resp.headers

    def test_returns_304_with_future_cursor(self, client):
        with patch("app.api.recurring_rules.recurring_rule_service") as svc:
            svc.get_filtered.return_value = ([], 0)
            resp = client.get(
                "/api/v1/recurring-rules",
                headers={**_auth_headers(), "If-Sync-Cursor": future_cursor()},
            )
        assert resp.status_code == 304
        assert "X-Sync-Cursor" in resp.headers

    def test_incremental_mode_returns_flat_list(self, client):
        mock_rule = _make_mock_rule()
        with patch("app.api.recurring_rules.recurring_rule_service") as svc:
            svc.get_filtered.return_value = ([mock_rule], 1)
            resp = client.get(
                "/api/v1/recurring-rules",
                headers={**_auth_headers(), "If-Sync-Cursor": past_cursor()},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data["data"], list)

    def test_requires_auth(self, client):
        resp = client.get("/api/v1/recurring-rules")
        assert resp.status_code == 401

    def test_full_sync_response_includes_cursor_header(self, client):
        with patch("app.api.recurring_rules.recurring_rule_service") as svc:
            svc.get_filtered.return_value = ([], 0)
            resp = client.get("/api/v1/recurring-rules", headers=_auth_headers())
        assert "X-Sync-Cursor" in resp.headers


# ---------------------------------------------------------------------------
# API tests — POST /api/v1/recurring-rules
# ---------------------------------------------------------------------------

class TestCreateRecurringRule:
    """POST /api/v1/recurring-rules"""

    def test_create_returns_201(self, client):
        mock_rule = _make_mock_rule()
        with patch("app.api.recurring_rules.recurring_rule_service") as svc, \
             patch("app.api.recurring_rules._repo") as repo:
            repo.get_by_offline_id.return_value = None
            svc.create.return_value = mock_rule
            resp = client.post(
                "/api/v1/recurring-rules",
                json=_valid_create_payload(),
                headers=_auth_headers(),
            )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["title"] == "Netflix"

    def test_create_returns_409_on_duplicate_offline_id(self, client):
        mock_rule = _make_mock_rule()
        with patch("app.api.recurring_rules._repo") as repo:
            repo.get_by_offline_id.return_value = mock_rule
            resp = client.post(
                "/api/v1/recurring-rules",
                json=_valid_create_payload(),
                headers=_auth_headers(),
            )
        assert resp.status_code == 409
        data = resp.get_json()
        assert data["success"] is False

    def test_create_returns_400_on_missing_required_fields(self, client):
        resp = client.post(
            "/api/v1/recurring-rules",
            json={"title": "no required fields"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400

    def test_create_returns_400_on_negative_amount(self, client):
        payload = _valid_create_payload()
        payload["amount"] = "-10.00"
        resp = client.post(
            "/api/v1/recurring-rules",
            json=payload,
            headers=_auth_headers(),
        )
        assert resp.status_code == 400

    def test_requires_auth(self, client):
        resp = client.post("/api/v1/recurring-rules", json=_valid_create_payload())
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# API tests — PATCH /api/v1/recurring-rules/<id>
# ---------------------------------------------------------------------------

class TestUpdateRecurringRule:
    """PATCH /api/v1/recurring-rules/<id>"""

    def test_update_returns_200(self, client):
        rule_id = uuid4()
        mock_rule = _make_mock_rule(rule_id)
        with patch("app.api.recurring_rules.recurring_rule_service") as svc:
            svc.get_by_id.return_value = mock_rule
            svc.update.return_value = mock_rule
            resp = client.patch(
                f"/api/v1/recurring-rules/{rule_id}",
                json={"title": "Disney+"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_update_returns_404_for_wrong_user(self, client):
        rule_id = uuid4()
        from app.utils.exceptions import NotFoundError
        with patch("app.api.recurring_rules.recurring_rule_service") as svc:
            svc.update.side_effect = NotFoundError("RecurringRule", str(rule_id))
            resp = client.patch(
                f"/api/v1/recurring-rules/{rule_id}",
                json={"title": "X"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_update_returns_409_on_lww_conflict(self, client):
        rule_id = uuid4()
        mock_rule = _make_mock_rule(rule_id)
        # Server updated_at is in the future relative to client header
        mock_rule.updated_at = datetime.now(timezone.utc) + timedelta(hours=1)
        past_client_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        with patch("app.api.recurring_rules.recurring_rule_service") as svc:
            svc.get_by_id.return_value = mock_rule
            resp = client.patch(
                f"/api/v1/recurring-rules/{rule_id}",
                json={"title": "X"},
                headers={
                    **_auth_headers(),
                    "X-Client-Updated-At": past_client_ts,
                },
            )
        assert resp.status_code == 409

    def test_requires_auth(self, client):
        resp = client.patch(f"/api/v1/recurring-rules/{uuid4()}", json={})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# API tests — DELETE /api/v1/recurring-rules/<id>
# ---------------------------------------------------------------------------

class TestDeleteRecurringRule:
    """DELETE /api/v1/recurring-rules/<id>"""

    def test_delete_returns_204(self, client):
        rule_id = uuid4()
        with patch("app.api.recurring_rules.recurring_rule_service") as svc:
            svc.delete.return_value = None
            resp = client.delete(
                f"/api/v1/recurring-rules/{rule_id}",
                headers=_auth_headers(),
            )
        assert resp.status_code == 204

    def test_delete_returns_404_for_wrong_user(self, client):
        rule_id = uuid4()
        from app.utils.exceptions import NotFoundError
        with patch("app.api.recurring_rules.recurring_rule_service") as svc:
            svc.delete.side_effect = NotFoundError("RecurringRule", str(rule_id))
            resp = client.delete(
                f"/api/v1/recurring-rules/{rule_id}",
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client):
        resp = client.delete(f"/api/v1/recurring-rules/{uuid4()}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# API tests — POST /api/v1/transactions with recurring_rule_id
# ---------------------------------------------------------------------------

class TestTransactionWithRecurringRuleId:
    """POST /api/v1/transactions — verify recurring_rule_id is accepted."""

    def test_transaction_create_with_recurring_rule_id(self, client):
        from app.models.transaction import TransactionType
        rule_id = uuid4()

        mock_tx = MagicMock()
        mock_tx.id = uuid4()
        mock_tx.type = TransactionType.EXPENSE
        mock_tx.amount = Decimal("15.99")
        mock_tx.date = date(2026, 4, 1)
        mock_tx.account_id = uuid4()
        mock_tx.category_id = uuid4()
        mock_tx.title = "Netflix"
        mock_tx.description = None
        mock_tx.tags = []
        mock_tx.original_amount = None
        mock_tx.original_currency = None
        mock_tx.exchange_rate = None
        mock_tx.base_rate = None
        mock_tx.recurring_rule_id = rule_id
        mock_tx.offline_id = f"t-{uuid4().hex}"
        mock_tx.created_at = datetime.utcnow()
        mock_tx.updated_at = datetime.utcnow()

        with patch("app.api.transactions.transaction_service") as svc:
            svc.create.return_value = mock_tx
            resp = client.post(
                "/api/v1/transactions",
                json={
                    "type": "expense",
                    "amount": "15.99",
                    "date": "2026-04-01",
                    "account_id": str(uuid4()),
                    "category_id": str(uuid4()),
                    "title": "Netflix",
                    "recurring_rule_id": str(rule_id),
                },
                headers=_auth_headers(),
            )

        assert resp.status_code == 201
        # Verify service was called with recurring_rule_id
        call_kwargs = svc.create.call_args.kwargs
        assert call_kwargs.get("recurring_rule_id") == rule_id
