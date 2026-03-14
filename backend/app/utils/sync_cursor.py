"""Sync cursor encoding/decoding utilities for incremental sync.

The cursor is an opaque base64url-encoded JSON string with the format:
    base64url({"t": "ISO_UTC_Z", "v": 1})

This module provides encode_cursor() and decode_cursor() for producing and
consuming the X-Sync-Cursor HTTP header value used in incremental sync
endpoints.
"""

import base64
import json
from datetime import datetime, timezone


def _now(tz=None) -> datetime:
    """Injectable clock for tests.

    Args:
        tz: Timezone to pass to datetime.now(). Defaults to UTC.

    Returns:
        Current datetime in the given timezone (UTC by default).
    """
    return datetime.now(tz or timezone.utc)


def encode_cursor() -> str:
    """Encode the current UTC timestamp as an opaque base64url cursor string.

    Produces a base64url-encoded JSON payload of the form:
        {"t": "2026-03-14T10:00:00.000000Z", "v": 1}

    Trailing ``=`` padding characters are stripped so the value is safe to
    embed directly in an HTTP header without quoting.

    Returns:
        A non-empty, padding-free base64url string representing the cursor.
    """
    ts = _now(timezone.utc)
    payload = json.dumps({"t": ts.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z", "v": 1})
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_cursor(header: str | None) -> datetime | None:
    """Decode an opaque cursor string back to a naive UTC datetime.

    The returned datetime has ``tzinfo=None`` (naive UTC), matching the
    convention used by ``BaseModel.updated_at`` throughout the application.

    This function is intentionally lenient: it returns ``None`` silently for
    any invalid or unrecognised input and NEVER raises an exception.

    Invalid inputs that produce ``None``:
    - ``None`` or empty string
    - Non-base64 data
    - Valid base64 that does not decode to JSON
    - JSON that is not a dict, or is missing the ``"t"`` key
    - Unknown version (``v != 1``)
    - Unparseable timestamp string in ``"t"``

    Args:
        header: The raw cursor string from the ``X-Sync-Cursor`` request
            header, or ``None`` if the header was absent.

    Returns:
        A naive ``datetime`` (UTC, tzinfo stripped) representing the cursor
        timestamp, or ``None`` if the input was absent or invalid.

        Naive datetime for compatibility with BaseModel.updated_at (also naive).
        If BaseModel.updated_at is ever migrated to timezone-aware datetimes,
        this function must be updated to stop stripping tzinfo.
    """
    if not header:
        return None
    try:
        padding = 4 - len(header) % 4
        padded = header + ("=" * padding if padding != 4 else "")
        data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if not isinstance(data, dict) or data.get("v") != 1:
            return None
        t = data.get("t")
        if not isinstance(t, str) or not t:
            return None
        return datetime.fromisoformat(t.rstrip("Z")).replace(tzinfo=None)
    except Exception:
        return None
