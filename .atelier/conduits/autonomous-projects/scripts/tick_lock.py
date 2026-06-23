"""Single-flight wrapper for an autonomous-projects tick.

Run a command while holding an OS advisory lock so a scheduled tick that
overruns its interval can't start a second run racing over the same project
files. If the lock is already held, bow out cleanly (skip note, exit 0). The
kernel releases the lock when the holder exits -- crash, kill, or timeout -- so
a dead run never jams the loop.

CLI: python3 tick_lock.py [--lock-file PATH] CMD [ARGS...]

Lock path: --lock-file, else $TICK_LOCK_FILE, else <cwd>/.autonomous-projects.lock.
# ponytail: per-cwd lock; pass --lock-file if you drive multiple roots from one cwd.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import subprocess
import sys


def _lock_path(cli: str | None) -> str:
    return cli or os.environ.get("TICK_LOCK_FILE") or os.path.join(
        os.getcwd(), ".autonomous-projects.lock"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock-file", default=None)
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.cmd:
        parser.error("a command to run is required")

    lock_file = _lock_path(args.lock_file)
    try:
        fd = os.open(lock_file, os.O_CREAT | os.O_RDWR, 0o644)
    except OSError as exc:
        # ponytail: open-error fails open; a broken lock must never jam the loop.
        print(f"tick_lock: cannot open {lock_file} ({exc}); running unguarded", file=sys.stderr)
        return subprocess.run(args.cmd).returncode

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        # ponytail: contention never fails open -- that would defeat single-flight.
        print("a tick is already running, skipping this one")
        os.close(fd)
        return 0

    # Hold the lock for the child's whole lifetime; the kernel drops it when this
    # parent exits (incl. crash/kill), which is what makes recovery automatic.
    try:
        return subprocess.run(args.cmd).returncode
    finally:
        os.close(fd)


if __name__ == "__main__":
    sys.exit(main())
