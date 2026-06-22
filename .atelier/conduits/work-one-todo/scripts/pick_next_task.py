"""Emit the highest-priority to-do filename so task selection is deterministic.

The advance step used to "pick the top .md in 01_to-do/" — undefined, so an AI
agent chose whatever it grabbed and the same queue could be worked in a
different order every run. This sorts by (priority asc, filename asc), mirroring
select_project.py, so a task's `priority` actually steers the queue and the same
queue is always worked in the same order.

ponytail: ~6-line frontmatter read beats a cross-conduit import of the gates
package — {{conduit_dir}} won't resolve to it from work-one-todo.

Stdout contract (always exit 0):
    <bare filename>   the chosen to-do file
    <empty>           01_to-do/ has no .md (or is missing/unreadable)
"""

from __future__ import annotations

import sys
from pathlib import Path


def _priority(md_path: Path) -> float:
    """Read `priority:` from the leading --- frontmatter; least-urgent on miss.

    Missing/blank/non-integer priority sorts last (float('inf')) so existing
    tasks with no priority still run, just behind anything explicitly set.
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return float("inf")
    if not text.startswith("---"):
        return float("inf")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return float("inf")
    for line in parts[1].splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "priority":
            try:
                return int(value.strip())
            except ValueError:
                return float("inf")
    return float("inf")


def pick_next_task(project_dir: str | Path) -> str:
    """Return the bare filename of the highest-priority to-do task, or ''.

    :param project_dir: project folder holding the numbered stage subfolders.
    :returns: chosen filename (priority asc, name asc), or '' if none/unreadable.
    """
    to_do = Path(project_dir) / "01_to-do"
    try:
        candidates = [p for p in to_do.glob("*.md") if p.is_file()]
    except OSError:
        return ""
    if not candidates:
        return ""
    candidates.sort(key=lambda p: (_priority(p), p.name))
    return candidates[0].name


def main() -> None:
    project_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    print(pick_next_task(project_dir))


if __name__ == "__main__":
    main()
