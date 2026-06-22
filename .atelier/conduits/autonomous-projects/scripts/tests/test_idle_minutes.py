"""Self-check for idle_minutes parsing. Run: python3 tests/test_idle_minutes.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from idle_minutes import DEFAULT_HOURS, to_minutes


def test_valid_value():
    assert to_minutes("0.1") == 6.0


def test_integer_string():
    assert to_minutes("2") == 120.0


def test_blank_falls_back():
    assert to_minutes("") == DEFAULT_HOURS * 60.0


def test_non_numeric_falls_back():
    assert to_minutes("abc") == DEFAULT_HOURS * 60.0


def test_none_falls_back():
    assert to_minutes(None) == DEFAULT_HOURS * 60.0


def test_never_raises():
    for bad in ["", "  ", "abc", None, "1.2.3"]:
        to_minutes(bad)  # must not raise


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
