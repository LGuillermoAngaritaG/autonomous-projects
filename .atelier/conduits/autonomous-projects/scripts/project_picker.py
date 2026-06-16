"""Pick the next autonomous project to work on, or emit a SKIP reason.

Stdout contract (always exit 0):
    <project file stem>      (the chosen project name, nothing else)
  or
    SKIP: <human-readable reason>

Filters, in order:
    1. PAUSED gate (skip if project name exists in projects/paused/)
    2. In-progress gate (resume project with a task in in-progress/)
    3. Cap gate: drop a project only when ALL three task counts are at/over
       their frontmatter caps at once — idea_*.md in backlog/ >= max_ideas AND
       review_*.md in backlog/ >= max_reviews AND *.md in in-review/ >=
       max_to_review. A missing cap field means no cap for that dimension, so
       the project can never be all-three-full and stays eligible.
    4. Idle time = max(latest git commit, latest mtime under `location`)
    5. Sort survivors by frontmatter priority asc; ties broken by oldest
       project file mtime.

The pending-review cap is NOT enforced here — it only throttles to-do
execution, which the conduit gates separately. A project with a full
pending-review/ stays eligible so idea/review generation keeps running.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# ---------- frontmatter parsing ----------

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str] | None:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


# ---------- idle gate ----------

_IGNORE_DIRS = {".git", ".atelier", "node_modules", "__pycache__", ".venv",
                ".mypy_cache", ".pytest_cache", "dist", "build", ".next"}


def max_mtime_under(path: Path) -> float:
    """Return the newest mtime of any file under `path`. 0 if empty/missing."""
    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_mtime
    newest = 0.0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for fname in files:
            try:
                m = (Path(root) / fname).stat().st_mtime
                if m > newest:
                    newest = m
            except OSError:
                continue
    return newest


def emit_ready(path: Path, fm: dict[str, str]) -> None:
    del fm  # name-only contract; frontmatter no longer emitted
    # no trailing newline: output is interpolated raw into task paths
    sys.stdout.write(path.stem)


def git_last_commit_ts(path: Path) -> float:
    """Return Unix ts of last commit in `path`. 0 if not a repo or no commits."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "log", "-1", "--format=%ct"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0.0
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


# ---------- picker ----------

_KANBAN = ("backlog", "abandoned", "to-do", "in-progress", "in-review", "done")


class ProjectPicker:
    """Choose the next project to advance, or print a SKIP reason."""

    def __init__(self, root: Path, idle_hours: float) -> None:
        self.root = root
        self.idle_hours = idle_hours
        self.projects_dir = root / "projects" / "working"
        self.paused_dir = root / "projects" / "paused"
        self.tasks_dir = root / "tasks"

    def load_projects(self) -> list[tuple[Path, dict[str, str]]]:
        """PAUSED gate + frontmatter parse + ensure task folders exist."""
        files = sorted(self.projects_dir.glob("*.md"))
        paused_names: set[str] = set()
        if self.paused_dir.is_dir():
            paused_names = {f.stem for f in self.paused_dir.glob("*.md")}
        parsed: list[tuple[Path, dict[str, str]]] = []
        for f in files:
            if f.stem in paused_names:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(text)
            if fm is None:
                print(f"warn: skipping {f.name}: no frontmatter", file=sys.stderr)
                continue
            project_tasks = self.tasks_dir / f.stem
            for sub in _KANBAN:
                (project_tasks / sub).mkdir(parents=True, exist_ok=True)
            parsed.append((f, fm))
        return parsed

    def in_progress_winner(
        self, parsed: list[tuple[Path, dict[str, str]]]
    ) -> tuple[Path, dict[str, str]] | None:
        """Return the first project with a task in in-progress/, else None."""
        for f, fm in parsed:
            ip_dir = self.tasks_dir / f.stem / "in-progress"
            if ip_dir.is_dir() and any(ip_dir.glob("*.md")):
                return f, fm
        return None

    @staticmethod
    def _capped(fm: dict[str, str], key: str, count: int) -> bool:
        # missing or non-numeric field => no cap => never "full"
        if key not in fm:
            return False
        try:
            cap = int(str(fm[key]).strip())
        except ValueError:
            return False
        return count >= cap

    def caps_reached(self, stem: str, fm: dict[str, str]) -> bool:
        """True only when all three task counts are at/over their caps at once."""
        backlog = self.tasks_dir / stem / "backlog"
        in_review = self.tasks_dir / stem / "in-review"
        idea_n = len(list(backlog.glob("idea_*.md")))
        review_n = len(list(backlog.glob("review_*.md")))
        toreview_n = len(list(in_review.glob("*.md")))
        return (self._capped(fm, "max_ideas", idea_n)
                and self._capped(fm, "max_reviews", review_n)
                and self._capped(fm, "max_to_review", toreview_n))

    def is_idle(self, fm: dict[str, str], now: float) -> bool:
        """True when `location` has been untouched for at least idle_hours."""
        location = Path(fm.get("location", "")).expanduser()
        mtime = max_mtime_under(location)
        gtime = (git_last_commit_ts(location)
                 if fm.get("use_git", "").lower() == "true" else 0.0)
        last_touched = max(mtime, gtime)
        return (now - last_touched) >= self.idle_hours * 3600.0

    def pick(self) -> int:
        """Run the gates and print the READY/SKIP contract; always returns 0."""
        if not self.root.is_dir():
            print(f"SKIP: projects_dir does not exist: {self.root}")
            return 0
        if not self.projects_dir.is_dir():
            print(f"SKIP: projects/working/ not found under {self.root}")
            return 0
        if not any(self.projects_dir.glob("*.md")):
            print(f"SKIP: no .md files in {self.projects_dir}")
            return 0

        # 1. PAUSED gate + parse + ensure folders
        parsed = self.load_projects()
        total = len(parsed)

        # 2. In-progress gate — resume an unfinished task (bypasses caps/idle)
        resume = self.in_progress_winner(parsed)
        if resume is not None:
            emit_ready(*resume)
            return 0

        # 3-4. Cap gate + idle gate
        now = time.time()
        capped = idle_filtered = 0
        survivors: list[tuple[Path, dict[str, str]]] = []
        for f, fm in parsed:
            if self.caps_reached(f.stem, fm):
                capped += 1
                continue
            if not self.is_idle(fm, now):
                idle_filtered += 1
                continue
            survivors.append((f, fm))

        if not survivors:
            print(
                f"SKIP: no eligible project "
                f"({capped} capped, {idle_filtered} idle, {total} total)"
            )
            return 0

        # Sort: priority asc (1 = highest); tie-break on oldest project-file mtime
        def sort_key(entry: tuple[Path, dict[str, str]]) -> tuple[int, float]:
            f, fm = entry
            try:
                prio = int(fm.get("priority", "999"))
            except ValueError:
                prio = 999
            try:
                proj_mtime = f.stat().st_mtime
            except OSError:
                proj_mtime = 0.0
            return prio, proj_mtime

        survivors.sort(key=sort_key)
        emit_ready(*survivors[0])
        return 0


# ---------- main ----------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects-dir",
                        default=str(Path(__file__).resolve().parent),
                        help="Conduit root holding projects/ and tasks/. "
                             "Defaults to this script's directory.")
    parser.add_argument("--idle-hours", type=float, required=True,
                        help="Project must be untouched for this many hours.")
    args = parser.parse_args()

    picker = ProjectPicker(
        root=Path(args.projects_dir).expanduser(),
        idle_hours=args.idle_hours,
    )
    return picker.pick()


if __name__ == "__main__":
    sys.exit(main())
