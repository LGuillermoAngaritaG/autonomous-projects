"""Self-check for usage_gate role throttling. Run: python3 tests/test_usage_gate.py"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from usage_gate import _ceiling, read_project_ceilings, role_ok

CEILINGS = {"claudecode": 80, "codex": 95, "opencode": 85}


def test_under_ceiling_open():
    assert role_ok("cc", {"claudecode": 50}, CEILINGS) is True


def test_at_or_over_ceiling_closed():
    assert role_ok("cc", {"claudecode": 80}, CEILINGS) is False
    assert role_ok("codex", {"codex": 96}, CEILINGS) is False


def test_unreadable_usage_fails_open():
    # Empty usage dict (broken read) -> treated as 0% -> never throttled.
    assert role_ok("opencode", {}, CEILINGS) is True


def test_unknown_harness_not_throttled():
    assert role_ok("", {"claudecode": 99}, CEILINGS) is True
    assert role_ok("bogus", {"claudecode": 99}, CEILINGS) is True


def test_ceiling_garbage_is_no_limit():
    # Empty/non-numeric override -> 100 (no limit), so the gate never crashes
    # and the role stays open. Valid numbers still parse.
    assert _ceiling("") == 100
    assert _ceiling("foo") == 100
    assert _ceiling(None) == 100
    assert _ceiling("80") == 80
    # An unparseable ceiling leaves the role open (0% usage < 100).
    assert role_ok("cc", {"claudecode": 0}, {"claudecode": _ceiling("")}) is True


def _make_md(text: str) -> str:
    tmp = Path(tempfile.mkdtemp()) / "project.md"
    tmp.write_text(text, encoding="utf-8")
    return str(tmp)


def test_read_project_ceilings_wins():
    path = _make_md("---\npriority: 1\nmax_usage_cc: 50\nmax_usage_codex: 90\n---\n")
    assert read_project_ceilings(path) == {"max_usage_cc": 50, "max_usage_codex": 90}


def test_read_project_ceilings_absent_falls_back():
    path = _make_md("---\npriority: 1\n---\n")
    assert read_project_ceilings(path) == {}


def test_read_project_ceilings_missing_file_falls_back():
    assert read_project_ceilings("/nonexistent/path.md") == {}
    assert read_project_ceilings("") == {}


def test_read_project_ceilings_malformed_falls_back():
    path = _make_md("not frontmatter")
    assert read_project_ceilings(path) == {}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("all passed")
