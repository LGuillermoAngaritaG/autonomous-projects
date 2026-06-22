"""Self-check for tick_lock mutual exclusion. Run: python3 tests/test_tick_lock.py"""

import fcntl
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tick_lock import _lock_path


def _flock(path: str) -> int:
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return fd


def test_mutual_exclusion_then_release_readmits():
    path = str(Path(tempfile.mkdtemp()) / "t.lock")
    fd = _flock(path)
    # A second non-blocking lock on the same path is refused -> single-flight.
    with pytest.raises(BlockingIOError):
        _flock(path)
    # Closing the holder (run end / death) re-admits the next run -> no stale jam.
    os.close(fd)
    fd2 = _flock(path)
    os.close(fd2)


def test_lock_path_precedence(monkeypatch):
    monkeypatch.delenv("TICK_LOCK_FILE", raising=False)
    assert _lock_path("/cli/path") == "/cli/path"
    monkeypatch.setenv("TICK_LOCK_FILE", "/env/path")
    assert _lock_path(None) == "/env/path"
    monkeypatch.delenv("TICK_LOCK_FILE", raising=False)
    assert _lock_path(None) == os.path.join(os.getcwd(), ".autonomous-projects.lock")


if __name__ == "__main__":
    # Minimal runner mirroring test_usage_gate.py (no pytest fixtures here).
    test_mutual_exclusion_then_release_readmits()
    print("ok test_mutual_exclusion_then_release_readmits")
    print("all passed")
