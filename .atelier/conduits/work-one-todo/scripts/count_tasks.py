"""Count .md files in a folder and emit 'task_counter: N'; always exit 0.

Safe default + one-line warning on any failure so a missing/unreadable folder
never crashes the tick branch.

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
