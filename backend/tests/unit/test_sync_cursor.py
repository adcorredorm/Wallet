"""Unit tests for backend/app/utils/sync_cursor.py.

Tests follow TDD: written before the implementation, verifying encode/decode
contract for the opaque base64url cursor used in incremental sync.
"""

import base64
import json
from datetime import datetime, timezone, timedelta

import pytest

from app.utils.sync_cursor import decode_cursor, encode_cursor


# ---------------------------------------------------------------------------
# encode tests
# ---------------------------------------------------------------------------


def test_encode_returns_nonempty_string() -> None:
    """encode_cursor() must return a non-empty string."""
    result = encode_cursor()
    assert isinstance(result, str)
    assert len(result) > 0


def test_encode_decode_roundtrip() -> None:
    """A cursor produced by encode_cursor() must round-trip through decode_cursor().

    The decoded datetime must have tzinfo=None (naive UTC), matching
    BaseModel.updated_at convention.
    """
    cursor = encode_cursor()
    decoded = decode_cursor(cursor)
    assert decoded is not None
    assert isinstance(decoded, datetime)
    assert decoded.tzinfo is None  # must be naive


# ---------------------------------------------------------------------------
# decode — None / empty / malformed input
# ---------------------------------------------------------------------------


def test_decode_none_returns_none() -> None:
    """decode_cursor(None) must return None silently."""
    assert decode_cursor(None) is None


def test_decode_empty_string_returns_none() -> None:
    """decode_cursor('') must return None silently."""
    assert decode_cursor("") is None


def test_decode_invalid_base64_returns_none() -> None:
    """Non-base64 garbage must return None without raising."""
    assert decode_cursor("!!!not-base64!!!") is None


def test_decode_invalid_json_returns_none() -> None:
    """Valid base64 that does not decode to JSON must return None."""
    bad_json = base64.urlsafe_b64encode(b"not json at all").decode().rstrip("=")
    assert decode_cursor(bad_json) is None


def test_decode_missing_t_field_returns_none() -> None:
    """Cursor JSON without the 't' key must return None."""
    payload = json.dumps({"v": 1, "other": "value"}).encode()
    cursor = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    assert decode_cursor(cursor) is None


def test_decode_unknown_version_returns_none() -> None:
    """Cursor with v=999 (unknown version) must return None."""
    payload = json.dumps({"t": "2026-03-14T10:00:00.000000Z", "v": 999}).encode()
    cursor = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    assert decode_cursor(cursor) is None


def test_decode_invalid_timestamp_returns_none() -> None:
    """Cursor with a non-ISO timestamp string must return None."""
    payload = json.dumps({"t": "not-a-date", "v": 1}).encode()
    cursor = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    assert decode_cursor(cursor) is None


def test_decode_t_field_null_returns_none() -> None:
    """Cursor with t=null must return None (non-string t is rejected)."""
    payload = base64.urlsafe_b64encode(
        json.dumps({"t": None, "v": 1}).encode()
    ).decode()
    assert decode_cursor(payload) is None


# ---------------------------------------------------------------------------
# decoded value sanity
# ---------------------------------------------------------------------------


def test_decoded_timestamp_is_close_to_now() -> None:
    """The decoded timestamp must be within 5 seconds of wall-clock UTC now."""
    cursor = encode_cursor()
    decoded = decode_cursor(cursor)
    assert decoded is not None
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    delta = abs((now_naive - decoded).total_seconds())
    assert delta < 5


def test_two_cursors_have_different_timestamps(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two encode_cursor() calls with distinct injected times produce distinct cursors.

    Patches _now via monkeypatch to control the clock deterministically.
    """
    import app.utils.sync_cursor as mod

    t1 = datetime(2026, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(seconds=60)

    monkeypatch.setattr(mod, "_now", lambda tz=None: t1)
    cursor1 = encode_cursor()

    monkeypatch.setattr(mod, "_now", lambda tz=None: t2)
    cursor2 = encode_cursor()

    assert cursor1 != cursor2

    decoded1 = decode_cursor(cursor1)
    decoded2 = decode_cursor(cursor2)
    assert decoded1 is not None
    assert decoded2 is not None
    assert decoded2 > decoded1
