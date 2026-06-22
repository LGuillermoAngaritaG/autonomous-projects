"""Emit 'remaining: N' (cap minus files present), always exit 0.

Print a safe default on any failure + one-line warning to stderr, so a broken
folder or unreadable project.md never crashes the tick branch.

Stdout contract (always exit 0):
    remaining: <int>

Failure mode: prints 'remaining: 0' and a 'warning:' line to stderr naming
what went wrong.
"""

from __future__ import annotations

import argparse
import os
import sys


def parse_cap(doc_path: str, cap_key: str) -> int:
    """Read cap_key from project.md frontmatter. Returns parsed int or 0."""
    try:
        with open(doc_path) as f:
            for line in f:
                line_lower = line.lower().strip()
                if line_lower.startswith(cap_key.lower() + ":"):
                    val = line_lower.split(":", 1)[1].strip()
                    digits = "".join(ch for ch in val if ch.isdigit())
                    if digits:
                        return int(digits)
                    return 0
    except Exception:
        pass
    return 0


def count_files(folder: str, prefix: str) -> int:
    """Count files matching `<prefix>*` in folder. Returns 0 on any error."""
    try:
        return sum(
            1
            for name in os.listdir(folder)
            if name.startswith(prefix) and os.path.isfile(os.path.join(folder, name))
        )
    except Exception:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc", required=True)
    parser.add_argument("--folder", required=True)
    parser.add_argument("--cap-key", required=True)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()

    cap = parse_cap(args.doc, args.cap_key)
    count = count_files(args.folder, args.prefix)
    remaining = max(cap - count, 0)
    print(f"remaining: {remaining}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
