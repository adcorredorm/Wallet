# backend/tests/test_budgets.py
import json
import base64
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import jwt
import pytest
from unittest.mock import patch, MagicMock


_TEST_USER_ID = uuid4()
_JWT_SECRET = "test-jwt-secret-for-testing-only"


def _auth_headers(user_id=None) -> dict:
    uid = user_id or _TEST_USER_ID
    payload = {
        "sub": str(uid),
        "email": "budget-test@example.com",
        "name": "Budget Test",
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


@pytest.fixture(autouse=True)
def ensure_test_user(app):
    from app.extensions import db
    from app.models.user import User
    with app.app_context():
        existing = db.session.get(User, _TEST_USER_ID)
        if existing is None:
            user = User(
                id=_TEST_USER_ID,
                google_id=f"google-bgt-{str(_TEST_USER_ID)[:8]}",
                email="budget-test@example.com",
                name="Budget Test",
            )
            db.session.add(user)
            db.session.commit()


class TestBudgetModel:
    def test_enum_values(self):
        from app.models.budget import BudgetType, BudgetStatus, BudgetFrequency
        assert BudgetType.RECURRING.value == "recurring"
        assert BudgetType.ONE_TIME.value == "one_time"
        assert BudgetStatus.ACTIVE.value == "active"
        assert BudgetStatus.ARCHIVED.value == "archived"
        assert BudgetFrequency.MONTHLY.value == "monthly"

    def test_repr(self, app):
        from app.models.budget import Budget, BudgetType, BudgetStatus
        with app.app_context():
            b = Budget(
                user_id=_TEST_USER_ID,
                name="Comida",
                amount_limit=Decimal("500"),
                currency="MXN",
                budget_type=BudgetType.RECURRING,
                status=BudgetStatus.ACTIVE,
                account_id=uuid4(),
            )
            assert "Comida" in repr(b)
            assert "recurring" in repr(b)


class TestBudgetSchemas:
    def test_create_requires_exactly_one_scope(self):
        from app.schemas.budget import BudgetCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            BudgetCreate(offline_id="t1", name="X", account_id=uuid4(), category_id=uuid4(),
                         amount_limit=Decimal("100"), currency="MXN", budget_type="recurring", frequency="monthly")
        with pytest.raises(pydantic.ValidationError):
            BudgetCreate(offline_id="t2", name="X", amount_limit=Decimal("100"), currency="MXN",
                         budget_type="recurring", frequency="monthly")

    def test_create_recurring_requires_frequency(self):
        from app.schemas.budget import BudgetCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            BudgetCreate(offline_id="t3", name="X", account_id=uuid4(),
                         amount_limit=Decimal("100"), currency="MXN", budget_type="recurring")

    def test_create_one_time_requires_dates(self):
        from app.schemas.budget import BudgetCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            BudgetCreate(offline_id="t4", name="X", account_id=uuid4(),
                         amount_limit=Decimal("100"), currency="MXN", budget_type="one_time")

    def test_create_one_time_end_after_start(self):
        from app.schemas.budget import BudgetCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            BudgetCreate(offline_id="t5", name="X", account_id=uuid4(),
                         amount_limit=Decimal("100"), currency="MXN", budget_type="one_time",
                         start_date=date(2026, 4, 10), end_date=date(2026, 4, 1))

    def test_valid_recurring_schema(self):
        from app.schemas.budget import BudgetCreate
        b = BudgetCreate(offline_id="t6", name="Comida", account_id=uuid4(),
                         amount_limit=Decimal("500"), currency="MXN",
                         budget_type="recurring", frequency="monthly")
        assert b.name == "Comida"
        assert b.interval == 1


class TestBudgetService:
    @pytest.fixture
    def account_id(self, app):
        from app.extensions import db
        from app.models.account import Account, AccountType
        with app.app_context():
            acc = Account(user_id=_TEST_USER_ID, name=f"Acct-{uuid4().hex[:6]}",
                          type=AccountType.DEBIT, currency="MXN", active=True)
            db.session.add(acc)
            db.session.commit()
            return acc.id

    def _make_budget(self, service, account_id, **overrides):
        defaults = dict(user_id=_TEST_USER_ID, offline_id=f"test-{uuid4().hex}",
                        name="Comida", account_id=account_id, amount_limit=Decimal("500"),
                        currency="MXN", budget_type="recurring", frequency="monthly")
        defaults.update(overrides)
        return service.create(**defaults)

    def test_create_returns_budget(self, app, account_id):
        from app.services.budget import BudgetService
        with app.app_context():
            service = BudgetService()
            budget = self._make_budget(service, account_id)
            assert budget.id is not None
            assert budget.status.value == "active"

    def test_create_idempotent_on_offline_id(self, app, account_id):
        from app.services.budget import BudgetService
        with app.app_context():
            service = BudgetService()
            oid = f"idem-{uuid4().hex}"
            b1 = self._make_budget(service, account_id, offline_id=oid)
            b2 = self._make_budget(service, account_id, offline_id=oid)
            assert b1.id == b2.id

    def test_archive_sets_archived_status(self, app, account_id):
        from app.services.budget import BudgetService
        with app.app_context():
            service = BudgetService()
            budget = self._make_budget(service, account_id)
            archived = service.archive(budget.id, _TEST_USER_ID)
            assert archived.status.value == "archived"

    def test_get_active_excludes_archived(self, app, account_id):
        from app.services.budget import BudgetService
        with app.app_context():
            service = BudgetService()
            b = self._make_budget(service, account_id)
            service.archive(b.id, _TEST_USER_ID)
            active = service.get_active(user_id=_TEST_USER_ID)
            assert all(x.status.value != "archived" for x in active)

    def test_delete_removes_budget(self, app, account_id):
        from app.services.budget import BudgetService
        from app.utils.exceptions import NotFoundError
        with app.app_context():
            service = BudgetService()
            budget = self._make_budget(service, account_id)
            service.delete(budget.id, _TEST_USER_ID)
            with pytest.raises(NotFoundError):
                service.get_by_id(budget.id, _TEST_USER_ID)


def _make_mock_budget(budget_id=None):
    from app.models.budget import BudgetType, BudgetStatus, BudgetFrequency
    b = MagicMock()
    b.id = budget_id or uuid4()
    b.offline_id = f"offline-{uuid4().hex[:8]}"
    b.user_id = _TEST_USER_ID
    b.name = "Comida"
    b.account_id = uuid4()
    b.category_id = None
    b.amount_limit = Decimal("500")
    b.currency = "MXN"
    b.budget_type = BudgetType.RECURRING
    b.frequency = BudgetFrequency.MONTHLY
    b.interval = 1
    b.reference_date = None
    b.start_date = None
    b.end_date = None
    b.status = BudgetStatus.ACTIVE
    b.icon = None
    b.color = None
    b.created_at = datetime.utcnow()
    b.updated_at = datetime.utcnow()
    return b


def _valid_create_payload() -> dict:
    return {"offline_id": f"test-{uuid4().hex}", "name": "Comida", "account_id": str(uuid4()),
            "amount_limit": "500.00", "currency": "MXN", "budget_type": "recurring", "frequency": "monthly"}


class TestListBudgets:
    def test_returns_200(self, client):
        with patch("app.api.budgets.budget_service") as svc:
            svc.get_active.return_value = [_make_mock_budget()]
            resp = client.get("/api/v1/budgets", headers=_auth_headers())
        assert resp.status_code == 200
        assert "X-Sync-Cursor" in resp.headers

    def test_returns_304_with_future_cursor_and_no_data(self, client):
        with patch("app.api.budgets.budget_service") as svc:
            svc.get_active.return_value = []
            resp = client.get("/api/v1/budgets",
                              headers={**_auth_headers(), "If-Sync-Cursor": future_cursor()})
        assert resp.status_code == 304

    def test_requires_auth(self, client):
        assert client.get("/api/v1/budgets").status_code == 401


class TestCreateBudget:
    def test_create_returns_201(self, client):
        with patch("app.api.budgets.budget_service") as svc, \
             patch("app.api.budgets._repo") as repo:
            repo.get_by_offline_id.return_value = None
            svc.create.return_value = _make_mock_budget()
            resp = client.post("/api/v1/budgets", json=_valid_create_payload(), headers=_auth_headers())
        assert resp.status_code == 201
        assert resp.get_json()["success"] is True

    def test_invalid_scope_returns_400(self, client):
        payload = _valid_create_payload()
        payload["category_id"] = str(uuid4())
        assert client.post("/api/v1/budgets", json=payload, headers=_auth_headers()).status_code == 400

    def test_requires_auth(self, client):
        assert client.post("/api/v1/budgets", json=_valid_create_payload()).status_code == 401


class TestArchiveBudget:
    def test_archive_returns_204(self, client):
        with patch("app.api.budgets.budget_service") as svc:
            svc.archive.return_value = None
            resp = client.delete(f"/api/v1/budgets/{uuid4()}", headers=_auth_headers())
        assert resp.status_code == 204
