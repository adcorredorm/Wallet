"""
Tests for fee transaction FK behavior.

Schema tests: pure Pydantic — no DB needed.
API tests: real in-memory SQLite DB via the `app` fixture.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.transaction import TransactionCreate, TransactionResponse


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEST_USER_ID = uuid4()
_JWT_SECRET = "test-jwt-secret-for-testing-only"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _auth_headers(user_id=None) -> dict:
    import jwt
    uid = user_id or _TEST_USER_ID
    payload = {
        "sub": str(uid),
        "email": "fee-test@example.com",
        "name": "Fee Test",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, _JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# DB fixture: ensure test user exists
# ---------------------------------------------------------------------------

@pytest.fixture()
def ensure_test_user(app):
    from app.extensions import db
    from app.models.user import User

    with app.app_context():
        existing = db.session.get(User, _TEST_USER_ID)
        if existing is None:
            user = User(
                id=_TEST_USER_ID,
                google_id=f"google-fee-{str(_TEST_USER_ID)[:8]}",
                email="fee-test@example.com",
                name="Fee Test",
            )
            db.session.add(user)
            db.session.commit()


# ===========================================================================
# Schema tests (no DB)
# ===========================================================================

class TestTransactionCreateFeeSchema:
    """Pydantic validation for fee FK fields in TransactionCreate."""

    def _base_payload(self, **kwargs) -> dict:
        return dict(
            type="expense",
            amount=Decimal("50.00"),
            date=date.today(),
            account_id=uuid4(),
            category_id=uuid4(),
            **kwargs,
        )

    def test_fee_for_transaction_id_alone_is_valid(self):
        """TransactionCreate accepts fee_for_transaction_id when fee_for_transfer_id is absent."""
        parent_id = uuid4()
        schema = TransactionCreate(**self._base_payload(fee_for_transaction_id=parent_id))
        assert schema.fee_for_transaction_id == parent_id
        assert schema.fee_for_transfer_id is None

    def test_fee_for_transfer_id_alone_is_valid(self):
        """TransactionCreate accepts fee_for_transfer_id when fee_for_transaction_id is absent."""
        transfer_id = uuid4()
        schema = TransactionCreate(**self._base_payload(fee_for_transfer_id=transfer_id))
        assert schema.fee_for_transfer_id == transfer_id
        assert schema.fee_for_transaction_id is None

    def test_both_fee_fks_set_raises_validation_error(self):
        """TransactionCreate rejects payloads where both fee FKs are set simultaneously."""
        with pytest.raises(ValidationError) as exc_info:
            TransactionCreate(**self._base_payload(
                fee_for_transaction_id=uuid4(),
                fee_for_transfer_id=uuid4(),
            ))
        errors = exc_info.value.errors()
        assert any("fee_for" in str(e) for e in errors)

    def test_neither_fee_fk_set_defaults_to_none(self):
        """TransactionCreate defaults both fee FKs to None when neither is provided."""
        schema = TransactionCreate(**self._base_payload())
        assert schema.fee_for_transaction_id is None
        assert schema.fee_for_transfer_id is None


class TestTransactionResponseFeeSchema:
    """TransactionResponse includes fee FK fields."""

    def test_response_includes_fee_for_transaction_id(self):
        """TransactionResponse serializes fee_for_transaction_id correctly."""
        parent_id = uuid4()
        response = TransactionResponse(
            id=uuid4(),
            type="expense",
            amount=Decimal("50.00"),
            date=date.today(),
            account_id=uuid4(),
            category_id=uuid4(),
            title=None,
            description=None,
            tags=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            fee_for_transaction_id=parent_id,
            fee_for_transfer_id=None,
        )
        dumped = response.model_dump(mode="json")
        assert dumped["fee_for_transaction_id"] == str(parent_id)
        assert dumped["fee_for_transfer_id"] is None

    def test_response_fee_fks_default_to_none(self):
        """TransactionResponse fee FK fields default to None when not provided."""
        response = TransactionResponse(
            id=uuid4(),
            type="expense",
            amount=Decimal("50.00"),
            date=date.today(),
            account_id=uuid4(),
            category_id=uuid4(),
            title=None,
            description=None,
            tags=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert response.fee_for_transaction_id is None
        assert response.fee_for_transfer_id is None


# ===========================================================================
# API integration tests (real DB via `app` fixture)
# ===========================================================================

class TestFeeTransactionAPI:
    """
    Integration tests hitting POST /api/v1/transactions with fee FK fields.

    These tests use the real SQLite test DB created by the `app` fixture.
    They rely on `make_account`, `make_category`, `make_transaction`, and
    `make_transfer` conftest factories.
    """

    def test_create_fee_with_fee_for_transaction_id(
        self, client, ensure_test_user, make_account, make_category, make_transaction
    ):
        """
        POST /api/v1/transactions with fee_for_transaction_id set to a valid
        transaction ID should return 201 and include the FK in the response.
        """
        account = make_account(user_id=_TEST_USER_ID)
        category = make_category(user_id=_TEST_USER_ID)
        parent = make_transaction(
            account_id=account.id,
            category_id=category.id,
            user_id=_TEST_USER_ID,
        )

        payload = {
            "type": "expense",
            "amount": "2.50",
            "date": str(date.today()),
            "account_id": str(account.id),
            "category_id": str(category.id),
            "title": "Fee bancario",
            "fee_for_transaction_id": str(parent.id),
        }

        resp = client.post(
            "/api/v1/transactions",
            json=payload,
            headers=_auth_headers(),
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["fee_for_transaction_id"] == str(parent.id)
        assert body["data"]["fee_for_transfer_id"] is None

    def test_create_both_fee_fks_returns_400(
        self, client, ensure_test_user, make_account, make_category, make_transaction, make_transfer
    ):
        """
        POST /api/v1/transactions with both fee_for_transaction_id and
        fee_for_transfer_id set should return 400 (Pydantic validation error).
        """
        account = make_account(user_id=_TEST_USER_ID)
        category = make_category(user_id=_TEST_USER_ID)
        parent_tx = make_transaction(
            account_id=account.id,
            category_id=category.id,
            user_id=_TEST_USER_ID,
        )
        parent_transfer = make_transfer(
            source_account_id=account.id,
            user_id=_TEST_USER_ID,
        )

        payload = {
            "type": "expense",
            "amount": "2.50",
            "date": str(date.today()),
            "account_id": str(account.id),
            "category_id": str(category.id),
            "fee_for_transaction_id": str(parent_tx.id),
            "fee_for_transfer_id": str(parent_transfer.id),
        }

        resp = client.post(
            "/api/v1/transactions",
            json=payload,
            headers=_auth_headers(),
        )
        assert resp.status_code == 400

    def test_get_transaction_response_includes_fee_fk_fields(
        self, client, app, ensure_test_user, make_account, make_category, make_transaction
    ):
        """
        GET /api/v1/transactions/<id> for a fee transaction should include
        fee_for_transaction_id and fee_for_transfer_id in the response body.
        """
        from app.extensions import db
        from app.models.transaction import Transaction, TransactionType

        account = make_account(user_id=_TEST_USER_ID)
        category = make_category(user_id=_TEST_USER_ID)
        parent = make_transaction(
            account_id=account.id,
            category_id=category.id,
            user_id=_TEST_USER_ID,
        )

        with app.app_context():
            fee_tx = Transaction(
                user_id=_TEST_USER_ID,
                type=TransactionType.EXPENSE,
                amount=Decimal("1.00"),
                date=date.today(),
                account_id=account.id,
                category_id=category.id,
                title="Fee directo",
                fee_for_transaction_id=parent.id,
            )
            db.session.add(fee_tx)
            db.session.commit()
            db.session.refresh(fee_tx)
            fee_tx_id = fee_tx.id

        resp = client.get(
            f"/api/v1/transactions/{fee_tx_id}",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["fee_for_transaction_id"] == str(parent.id)
        assert body["data"]["fee_for_transfer_id"] is None
