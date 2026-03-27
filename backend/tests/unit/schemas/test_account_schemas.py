"""Unit tests for account Pydantic schemas — sort_order and icon fields."""

import pytest
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse
from datetime import datetime, timezone
from uuid import uuid4


class TestAccountCreateSchema:
    """sort_order and icon on AccountCreate."""

    def test_sort_order_defaults_to_none(self):
        """sort_order should be None when not provided (auto-assign signal)."""
        data = AccountCreate(name="Test", type="debit", currency="USD")
        assert data.sort_order is None

    def test_sort_order_accepts_zero(self):
        data = AccountCreate(name="Test", type="debit", currency="USD", sort_order=0)
        assert data.sort_order == 0

    def test_sort_order_accepts_positive_int(self):
        data = AccountCreate(name="Test", type="debit", currency="USD", sort_order=5)
        assert data.sort_order == 5

    def test_sort_order_rejects_negative(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AccountCreate(name="Test", type="debit", currency="USD", sort_order=-1)

    def test_icon_defaults_to_none(self):
        data = AccountCreate(name="Test", type="debit", currency="USD")
        assert data.icon is None

    def test_icon_accepts_emoji(self):
        data = AccountCreate(name="Test", type="debit", currency="USD", icon="💳")
        assert data.icon == "💳"

    def test_icon_rejects_string_over_50_chars(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AccountCreate(name="Test", type="debit", currency="USD", icon="x" * 51)


class TestAccountUpdateSchema:
    """sort_order and icon on AccountUpdate."""

    def test_sort_order_optional(self):
        data = AccountUpdate()
        assert data.sort_order is None

    def test_sort_order_accepts_zero(self):
        data = AccountUpdate(sort_order=0)
        assert data.sort_order == 0

    def test_sort_order_rejects_negative(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AccountUpdate(sort_order=-1)

    def test_icon_optional(self):
        data = AccountUpdate()
        assert data.icon is None

    def test_icon_accepts_emoji(self):
        data = AccountUpdate(icon="🏦")
        assert data.icon == "🏦"

    def test_icon_rejects_string_over_50_chars(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AccountUpdate(icon="x" * 51)


class TestAccountResponseSchema:
    """sort_order and icon on AccountResponse."""

    def _make_response_dict(self, **overrides):
        base = dict(
            id=uuid4(),
            name="Test",
            type="debit",
            currency="USD",
            description=None,
            tags=[],
            active=True,
            sort_order=0,
            icon=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        base.update(overrides)
        return base

    def test_sort_order_present_in_response(self):
        data = AccountResponse(**self._make_response_dict(sort_order=3))
        assert data.sort_order == 3

    def test_icon_present_and_nullable(self):
        data = AccountResponse(**self._make_response_dict(icon=None))
        assert data.icon is None

    def test_icon_present_with_value(self):
        data = AccountResponse(**self._make_response_dict(icon="💰"))
        assert data.icon == "💰"

    def test_sort_order_included_in_model_dump(self):
        data = AccountResponse(**self._make_response_dict(sort_order=7))
        dumped = data.model_dump(mode="json")
        assert dumped["sort_order"] == 7

    def test_icon_included_in_model_dump(self):
        data = AccountResponse(**self._make_response_dict(icon="💵"))
        dumped = data.model_dump(mode="json")
        assert dumped["icon"] == "💵"
