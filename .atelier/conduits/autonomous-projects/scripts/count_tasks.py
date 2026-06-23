"""Count .md files in a folder and emit 'task_counter: N'; always exit 0.

A missing or unreadable folder degrades to `task_counter: 0` (no warning) so a
broken read never crashes the tick branch. Shared by improve-task (inbox drain)
and work-one-todo (queue drain) to let a parent loop break on task_counter: 0.

Stdout contract (always exit 0):
    task_counter: <int>
"""

from __future__ import annotations

import os
import sys


def count_md_files(folder: str) -> int:
    """Count .md files in folder. Returns 0 on any error."""
    try:
        return sum(
            1
            for name in os.listdir(folder)
            if name.lower().endswith(".md") and os.path.isfile(os.path.join(folder, name))
        )
    except Exception:
        return 0


def main() -> None:
    folder = sys.argv[1] if len(sys.argv) > 1 else ""
    count = count_md_files(folder)
    print(f"task_counter: {count}")


if __name__ == "__main__":
    main()
