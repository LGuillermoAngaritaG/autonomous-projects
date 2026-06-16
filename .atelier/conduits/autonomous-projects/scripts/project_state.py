"""Emit per-tick gates for the project the picker chose.

Stdout contract (always exit 0):
    generate_idea: true|false
    generate_review: true|false
    work_on_to_do: true|false
    task_path: <abs path to the next to-do task, or empty>

Reads the project's frontmatter caps and counts its task files:
    generate_idea   -> backlog/idea_*.md   < max_ideas
    generate_review -> backlog/review_*.md < max_reviews
    work_on_to_do   -> a task waits in to-do/ or in-progress/
                       AND in-review/*.md  < max_to_review
A missing/non-numeric cap means no cap, so that gate stays open.

task_path is the top file in to-do/, ordered by: frontmatter priority asc,
then human-commented tasks first (non-empty `# User comments`), then review_*
files first. Empty string when to-do/ has no tasks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from project_picker import parse_frontmatter


def _section_has_content(text: str, header: str) -> bool:
    """True if the `# <header>` markdown section has any non-blank line."""
    in_section = False
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            if in_section:
                break
            in_section = line.strip().lstrip("#").strip() == header
            continue
        if in_section and line.strip():
            return True
    return False


class ProjectState:
    """Compute the per-tick conduit gates for one picked project."""

    def __init__(self, root: Path, name: str) -> None:
        self.project_file = root / "projects" / "working" / f"{name}.md"
        self.tasks = root / "tasks" / name

    @staticmethod
    def _under_cap(fm: dict[str, str], key: str, count: int) -> bool:
        """True when count is below the frontmatter cap, or the cap is absent."""
        raw = fm.get(key)
        if raw is None:
            return True
        try:
            return count < int(str(raw).strip())
        except ValueError:
            return True

    def _count(self, sub: str, pattern: str = "*.md") -> int:
        return len(list((self.tasks / sub).glob(pattern)))

    def gates(self) -> dict[str, bool]:
        """Return the three gate flags for this project."""
        text = self.project_file.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text) or {}
        has_work = self._count("to-do") > 0 or self._count("in-progress") > 0
        return {
            "generate_idea": self._under_cap(
                fm, "max_ideas", self._count("backlog", "idea_*.md")),
            "generate_review": self._under_cap(
                fm, "max_reviews", self._count("backlog", "review_*.md")),
            "work_on_to_do": has_work and self._under_cap(
                fm, "max_to_review", self._count("in-review")),
        }

    def next_task_path(self) -> str:
        """Path of the top to-do task, or "" when to-do/ is empty.

        Order: priority asc, then human-commented first, then review_ first.
        """
        files = list((self.tasks / "to-do").glob("*.md"))
        if not files:
            return ""

        def sort_key(f: Path) -> tuple[int, int, int, str]:
            text = f.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(text) or {}
            try:
                prio = int(str(fm.get("priority", "999")).strip())
            except ValueError:
                prio = 999
            commented = 0 if _section_has_content(text, "User comments") else 1
            review = 0 if f.name.startswith("review_") else 1
            return prio, commented, review, f.name

        return str(min(files, key=sort_key).resolve())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects-dir", required=True,
                        help="Conduit root holding projects/ and tasks/.")
    parser.add_argument("--name", required=True,
                        help="Project stem (the picker's NAME output).")
    args = parser.parse_args()

    state = ProjectState(Path(args.projects_dir).expanduser(), args.name)
    for key, val in state.gates().items():
        print(f"{key}: {str(val).lower()}")
    print(f"task_path: {state.next_task_path()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
