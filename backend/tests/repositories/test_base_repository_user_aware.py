"""Tests verifying BaseRepository methods filter by user_id."""
import pytest
from uuid import uuid4
from app.models.account import Account, AccountType
from app.repositories.account import AccountRepository


@pytest.fixture
def user_a_id(app):
    from app.models.user import User
    from app.extensions import db
    u = User(google_id="ga_unique", email="a_unique@test.com", name="A")
    db.session.add(u)
    db.session.commit()
    return u.id


@pytest.fixture
def user_b_id(app):
    from app.models.user import User
    from app.extensions import db
    u = User(google_id="gb_unique", email="b_unique@test.com", name="B")
    db.session.add(u)
    db.session.commit()
    return u.id


@pytest.fixture
def account_for_user_a(app, user_a_id):
    from app.extensions import db
    acc = Account(
        name="A's Account",
        type=AccountType.DEBIT,
        currency="COP",
        user_id=user_a_id,
    )
    db.session.add(acc)
    db.session.commit()
    return acc.id


def test_get_by_id_returns_none_for_wrong_user(app, account_for_user_a, user_b_id):
    """get_by_id with wrong user_id returns None, not the record."""
    repo = AccountRepository()
    result = repo.get_by_id(account_for_user_a, user_b_id)
    assert result is None


def test_get_by_id_returns_record_for_correct_user(app, account_for_user_a, user_a_id):
    """get_by_id with correct user_id returns the record."""
    repo = AccountRepository()
    result = repo.get_by_id(account_for_user_a, user_a_id)
    assert result is not None


def test_get_all_filters_by_user_id(app, account_for_user_a, user_a_id, user_b_id):
    """get_all on BaseRepository only returns records owned by the specified user."""
    from app.repositories.base import BaseRepository
    from app.models.account import Account

    # Use BaseRepository directly to test the user-aware base implementation,
    # bypassing AccountRepository's override (which is updated in Chunk 3).
    repo = BaseRepository(Account)
    a_records = repo.get_all(user_id=user_a_id)
    b_records = repo.get_all(user_id=user_b_id)
    assert len(a_records) >= 1
    assert all(r.user_id == user_a_id for r in a_records)
    assert len(b_records) == 0


def test_get_by_client_id_filters_by_user_id(app, user_a_id, user_b_id):
    """get_by_client_id does not return a record owned by a different user."""
    from app.extensions import db
    cid = "test-client-id-001"
    acc = Account(
        name="CID Account",
        type=AccountType.CASH,
        currency="USD",
        client_id=cid,
        user_id=user_a_id,
    )
    db.session.add(acc)
    db.session.commit()

    repo = AccountRepository()
    # User A should find it
    found = repo.get_by_client_id(cid, user_a_id)
    assert found is not None
    # User B should not
    not_found = repo.get_by_client_id(cid, user_b_id)
    assert not_found is None
