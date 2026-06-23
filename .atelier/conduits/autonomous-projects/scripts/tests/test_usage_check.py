"""Tests for usage_check.py harness resolution + fail-open gate logic.

Run: uv run pytest (from scripts/)
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from usage_check import _parse_usage, is_ok, resolve_harness


def _conduit(root: Path, name: str, body: str) -> None:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "conduit.yaml").write_text(body, encoding="utf-8")


def test_resolve_direct_harness(tmp_path):
    _conduit(tmp_path, "generate-idea", "tasks:\n  - go:\n      tool: harness:claude-code\n")
    assert resolve_harness("generate-idea", tmp_path) == "claude-code"


def test_resolve_follows_delegate(tmp_path):
    # work-one-todo declares no harness; it delegates to task-with-review.
    _conduit(
        tmp_path,
        "work-one-todo",
        "tasks:\n  - advance:\n      tool: tool:conduit\n      task: task-with-review\n",
    )
    _conduit(tmp_path, "task-with-review", "tasks:\n  - do:\n      tool: harness:claude-code\n")
    assert resolve_harness("work-one-todo", tmp_path) == "claude-code"


def test_resolve_unknown_returns_none(tmp_path):
    assert resolve_harness("nope", tmp_path) is None
    _conduit(tmp_path, "bare", "tasks:\n  - x:\n      tool: tool:bash\n")
    assert resolve_harness("bare", tmp_path) is None


def test_is_ok_under_ceiling():
    assert is_ok("claude-code", {"claudecode": 50}, 80) is True


def test_is_ok_at_or_over_ceiling():
    assert is_ok("claude-code", {"claudecode": 80}, 80) is False
    assert is_ok("claude-code", {"claudecode": 95}, 80) is False


def test_is_ok_unreadable_usage_fails_open():
    assert is_ok("claude-code", {}, 80) is True


def test_is_ok_unknown_harness_fails_open():
    assert is_ok(None, {"claudecode": 99}, 80) is True


def test_is_ok_unparseable_ceiling_fails_open():
    assert is_ok("claude-code", {"claudecode": 99}, None) is True


def test_parse_usage_strips_percent():
    assert _parse_usage("claudecode: 42%") == {"claudecode": 42}


def test_parse_usage_skips_na_and_junk():
    text = "claudecode: 42%\ncodex: n/a\nopencode: ???\ngarbage line"
    assert _parse_usage(text) == {"claudecode": 42}


def test_parse_usage_multiple_labels():
    text = "claudecode: 10%\ncodex: 20\nopencode: 30%"
    assert _parse_usage(text) == {"claudecode": 10, "codex": 20, "opencode": 30}


def test_parse_usage_empty():
    assert _parse_usage("") == {}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
