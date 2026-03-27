"""Unit tests for response helper functions."""
from decimal import Decimal
from enum import Enum

import pytest

from app.utils.responses import serialize_pydantic_errors


class _Color(Enum):
    RED = "red"


class _CustomObj:
    def __str__(self) -> str:
        return "custom-object"


def test_serialize_pydantic_errors_plain_string_ctx():
    """String ctx values pass through unchanged."""
    errors = [{"loc": ("field",), "msg": "bad", "type": "value_error", "ctx": {"error": "too short"}}]
    result = serialize_pydantic_errors(errors)
    assert result[0]["ctx"]["error"] == "too short"


def test_serialize_pydantic_errors_exception_in_ctx():
    """Exception objects in ctx are converted to str."""
    errors = [{"loc": ("x",), "msg": "err", "type": "value_error", "ctx": {"error": ValueError("boom")}}]
    result = serialize_pydantic_errors(errors)
    assert result[0]["ctx"]["error"] == "boom"


def test_serialize_pydantic_errors_decimal_in_ctx():
    """Decimal values in ctx are converted to str."""
    errors = [{"loc": ("amount",), "msg": "err", "type": "value_error", "ctx": {"limit_value": Decimal("9.99")}}]
    result = serialize_pydantic_errors(errors)
    assert result[0]["ctx"]["limit_value"] == "9.99"


def test_serialize_pydantic_errors_enum_in_ctx():
    """Enum values in ctx are converted to str."""
    errors = [{"loc": ("color",), "msg": "err", "type": "value_error", "ctx": {"expected": _Color.RED}}]
    result = serialize_pydantic_errors(errors)
    assert "RED" in result[0]["ctx"]["expected"]


def test_serialize_pydantic_errors_custom_object_in_ctx():
    """Custom objects in ctx are converted via str()."""
    errors = [{"loc": ("f",), "msg": "err", "type": "value_error", "ctx": {"obj": _CustomObj()}}]
    result = serialize_pydantic_errors(errors)
    assert result[0]["ctx"]["obj"] == "custom-object"


def test_serialize_pydantic_errors_nested_dict_in_ctx():
    """Nested dicts inside ctx are recursed into."""
    errors = [
        {
            "loc": ("f",),
            "msg": "err",
            "type": "value_error",
            "ctx": {"nested": {"inner": Decimal("1.5"), "ok": "fine"}},
        }
    ]
    result = serialize_pydantic_errors(errors)
    assert result[0]["ctx"]["nested"]["inner"] == "1.5"
    assert result[0]["ctx"]["nested"]["ok"] == "fine"


def test_serialize_pydantic_errors_list_in_ctx():
    """Lists inside ctx have each element processed."""
    errors = [
        {
            "loc": ("f",),
            "msg": "err",
            "type": "value_error",
            "ctx": {"allowed": [Decimal("1"), "two", 3]},
        }
    ]
    result = serialize_pydantic_errors(errors)
    assert result[0]["ctx"]["allowed"] == ["1", "two", 3]


def test_serialize_pydantic_errors_json_primitives_unchanged():
    """str, int, float, bool, None pass through as-is."""
    errors = [
        {
            "loc": ("f",),
            "msg": "err",
            "type": "value_error",
            "ctx": {"s": "hello", "i": 1, "f": 1.5, "b": True, "n": None},
        }
    ]
    result = serialize_pydantic_errors(errors)
    ctx = result[0]["ctx"]
    assert ctx["s"] == "hello"
    assert ctx["i"] == 1
    assert ctx["f"] == 1.5
    assert ctx["b"] is True
    assert ctx["n"] is None


def test_serialize_pydantic_errors_no_ctx():
    """Errors without ctx pass through without modification."""
    errors = [{"loc": ("f",), "msg": "required", "type": "missing"}]
    result = serialize_pydantic_errors(errors)
    assert result[0] == {"loc": ("f",), "msg": "required", "type": "missing"}


def test_serialize_pydantic_errors_multiple_errors():
    """Multiple errors in the list are all processed."""
    errors = [
        {"loc": ("a",), "msg": "e1", "type": "value_error", "ctx": {"error": Decimal("0")}},
        {"loc": ("b",), "msg": "e2", "type": "value_error", "ctx": {"error": ValueError("fail")}},
    ]
    result = serialize_pydantic_errors(errors)
    assert result[0]["ctx"]["error"] == "0"
    assert result[1]["ctx"]["error"] == "fail"
